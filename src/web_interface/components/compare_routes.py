import logging
from collections import namedtuple
from contextlib import suppress
from difflib import HtmlDiff

import lief
from flask import redirect, render_template, render_template_string, request, session, url_for
from flask_paginate import Pagination

from helperFunctions.database import ConnectTo
from helperFunctions.dataConversion import (
    convert_compare_id_to_list, convert_uid_list_to_compare_id, normalize_compare_id
)
from helperFunctions.web_interface import get_template_as_string
from intercom.front_end_binding import InterComFrontEndBinding
from storage.binary_service import BinaryService
from storage.db_interface_compare import CompareDbInterface, FactCompareException
from storage.db_interface_view_sync import ViewReader
from web_interface.components.component_base import ComponentBase
from web_interface.security.decorator import roles_accepted
from web_interface.security.privileges import PRIVILEGES


class CompareRoutes(ComponentBase):
    def _init_component(self):
        self._app.add_url_rule('/compare', '/compare/', self._app_show_start_compare)
        self._app.add_url_rule('/database/browse_compare', 'database/browse_compare', self._app_show_browse_compare)
        self._app.add_url_rule('/compare/<compare_id>', '/compare/<compare_id>', self._app_show_compare_result)
        self._app.add_url_rule('/comparison/add/<uid>', 'comparison/add/<uid>', self._add_to_compare_basket)
        self._app.add_url_rule('/comparison/remove/<analysis_uid>/<compare_uid>', 'comparison/remove/<analysis_uid>/<compare_uid>', self._remove_from_compare_basket)
        self._app.add_url_rule('/comparison/remove_all/<analysis_uid>', 'comparison/remove_all/<analysis_uid>', self._remove_all_from_compare_basket)
        self._app.add_url_rule('/file_pair_comparison/<uid1>/<uid2>', 'file_pair_comparison/<uid1>/<uid2>', self._compare_file_pair)

    @roles_accepted(*PRIVILEGES['compare'])
    def _app_show_compare_result(self, compare_id):
        compare_id = normalize_compare_id(compare_id)
        try:
            with ConnectTo(CompareDbInterface, self._config) as sc:
                result = sc.get_compare_result(compare_id)
        except FactCompareException as exception:
            return render_template('compare/error.html', error=exception.get_message())
        if not result:
            return render_template('compare/wait.html', compare_id=compare_id)
        download_link = self._create_ida_download_if_existing(result, compare_id)
        uid_list = convert_compare_id_to_list(compare_id)
        plugin_views, plugins_without_view = self._get_compare_plugin_views(result)
        compare_view = self._get_compare_view(plugin_views)
        self._fill_in_empty_fields(result, compare_id)
        return render_template_string(
            compare_view,
            result=result,
            uid_list=uid_list,
            download_link=download_link,
            plugins_without_view=plugins_without_view
        )

    @staticmethod
    def _fill_in_empty_fields(result, compare_id):
        compare_uids = compare_id.split(';')
        for key in result['general']:
            for uid in compare_uids:
                if uid not in result['general'][key]:
                    result['general'][key][uid] = ''

    def _get_compare_plugin_views(self, compare_result):
        views, plugins_without_view = [], []
        with suppress(KeyError):
            used_plugins = list(compare_result['plugins'].keys())
            for plugin in used_plugins:
                with ConnectTo(ViewReader, self._config) as vr:
                    view = vr.get_view(plugin)
                if view:
                    views.append((plugin, view))
                else:
                    plugins_without_view.append(plugin)
        return views, plugins_without_view

    def _get_compare_view(self, plugin_views):
        compare_view = get_template_as_string('compare/compare.html')
        return self._add_plugin_views_to_compare_view(compare_view, plugin_views)

    def _add_plugin_views_to_compare_view(self, compare_view, plugin_views):
        key = '{# individual plugin views #}'
        insertion_index = compare_view.find(key)
        if insertion_index == -1:
            logging.error('compare view insertion point not found in compare template')
        else:
            insertion_index += len(key)
            for plugin, view in plugin_views:
                if_case = '{{% elif plugin == \'{}\' %}}'.format(plugin)
                view = '{}\n{}'.format(if_case, view.decode())
                compare_view = self._insert_plugin_into_view_at_index(view, compare_view, insertion_index)
        return compare_view

    @staticmethod
    def _insert_plugin_into_view_at_index(plugin, view, index):
        if index < 0:
            return view
        return view[:index] + plugin + view[index:]

    @roles_accepted(*PRIVILEGES['submit_analysis'])
    def _app_show_start_compare(self):
        if 'uids_for_comparison' not in session or not isinstance(session['uids_for_comparison'], list) or len(session['uids_for_comparison']) < 2:
            return render_template('compare/error.html', error='No UIDs found for comparison')
        compare_id = convert_uid_list_to_compare_id(session['uids_for_comparison'])
        session['uids_for_comparison'] = None
        redo = True if request.args.get('force_recompare') else None

        with ConnectTo(CompareDbInterface, self._config) as sc:
            compare_exists = sc.compare_result_is_in_db(compare_id)
        if compare_exists and not redo:
            return redirect(url_for('/compare/<compare_id>', compare_id=compare_id))

        try:
            with ConnectTo(CompareDbInterface, self._config) as sc:
                sc.check_objects_exist(compare_id)
        except FactCompareException as exception:
            return render_template('compare/error.html', error=exception.get_message())

        with ConnectTo(InterComFrontEndBinding, self._config) as sc:
            sc.add_compare_task(compare_id, force=redo)
        return render_template('compare/wait.html', compare_id=compare_id)

    @staticmethod
    def _create_ida_download_if_existing(result, compare_id):
        if isinstance(result, dict) and result.get('plugins', dict()).get('Ida_Diff_Highlighting', dict()).get('idb_binary'):
            return '/ida-download/{}'.format(compare_id)
        return None

    @roles_accepted(*PRIVILEGES['compare'])
    def _app_show_browse_compare(self):
        page, per_page = self._get_page_items()[0:2]
        try:
            with ConnectTo(CompareDbInterface, self._config) as db_service:
                compare_list = db_service.page_compare_results(skip=per_page * (page - 1), limit=per_page)
        except Exception as exception:
            error_message = 'Could not query database: {} {}'.format(type(exception), str(exception))
            logging.error(error_message)
            return render_template('error.html', message=error_message)

        with ConnectTo(CompareDbInterface, self._config) as connection:
            total = connection.get_total_number_of_results()

        pagination = self._get_pagination(page=page, per_page=per_page, total=total, record_name='compare results', )
        return render_template('database/compare_browse.html', compare_list=compare_list, page=page, per_page=per_page, pagination=pagination)

    @staticmethod
    def _get_pagination(**kwargs):
        kwargs.setdefault('record_name', 'records')
        return Pagination(css_framework='bootstrap3', link_size='sm', show_single_page=False,
                          format_total=True, format_number=True, **kwargs)

    def _get_page_items(self):
        page = int(request.args.get('page', 1))
        per_page = request.args.get('per_page')
        if not per_page:
            per_page = int(self._config['database']['results_per_page'])
        else:
            per_page = int(per_page)
        offset = (page - 1) * per_page
        return page, per_page, offset

    @roles_accepted(*PRIVILEGES['submit_analysis'])
    def _add_to_compare_basket(self, uid):
        compare_uid_list = get_comparison_uid_list_from_session()
        compare_uid_list.append(uid)
        session.modified = True
        return redirect(url_for('analysis/<uid>', uid=uid))

    @roles_accepted(*PRIVILEGES['submit_analysis'])
    def _remove_from_compare_basket(self, analysis_uid, compare_uid):
        compare_uid_list = get_comparison_uid_list_from_session()
        if compare_uid in compare_uid_list:
            session['uids_for_comparison'].remove(compare_uid)
            session.modified = True
        return redirect(url_for('analysis/<uid>', uid=analysis_uid))

    @roles_accepted(*PRIVILEGES['submit_analysis'])
    def _remove_all_from_compare_basket(self, analysis_uid):
        compare_uid_list = get_comparison_uid_list_from_session()
        compare_uid_list.clear()
        session.modified = True
        return redirect(url_for('analysis/<uid>', uid=analysis_uid))

    @roles_accepted(*PRIVILEGES['compare'])
    def _compare_file_pair(self, uid1, uid2):
        bs = BinaryService(self._config)
        file1_fd, file_1_name = bs.get_binary_and_file_name(uid1)
        file2_fd, file_2_name = bs.get_binary_and_file_name(uid2)
        
        if self.is_text_file(uid1) and self.is_text_file(uid2):
            table = HtmlDiff(wrapcolumn=100).make_table(file1_fd.decode().splitlines(), file2_fd.decode().splitlines())
            table = table.replace('class="diff"', 'class="table table-bordered diff"')
            return render_template("compare/text_file_comparison.html", table=table, file1=file_1_name, file2=file_2_name)

        file1_elf, file2_elf = get_elf_data(file1_fd, file2_fd)
        if file1_elf is None or file2_elf is None:
            return render_template('compare/error.html', error='Both files must be of the same type (ELF)!')
        file1_data = {'uid': uid1,
                      'name': file_1_name,
                      'header': file1_elf.header,
                      'imported_libs': file1_elf.imported_libs,
                      'imported_functions': file1_elf.imported_functions,
                      'exported_functions': file1_elf.exported_functions,
                      'unique_strings': file1_elf.strings}
        file2_data = {'uid': uid2,
                      'name': file_2_name,
                      'header': file2_elf.header,
                      'imported_libs': file2_elf.imported_libs,
                      'imported_functions': file2_elf.imported_functions,
                      'exported_functions': file2_elf.exported_functions,
                      'unique_strings': file2_elf.strings}
        return render_template('compare/file_pair_comparison.html', file1=file1_data, file2=file2_data)

    def is_text_file(self, uid):
        with ConnectTo(CompareDbInterface, self._config) as db:
            if db.get_object(uid).processed_analysis['file_type']['mime'] == 'text/plain':
                return True
        return False


def get_comparison_uid_list_from_session():
    if 'uids_for_comparison' not in session or not isinstance(session['uids_for_comparison'], list):
        session['uids_for_comparison'] = []
    return session['uids_for_comparison']


def get_elf_data(file1, file2):
    ELF = namedtuple('ELF', 'header, imported_libs, imported_functions, exported_functions, strings')
    binary1 = lief.parse(file1)
    binary2 = lief.parse(file2)
    h1, h2 = None, None
    lib1, lib2 = None, None
    imported_functions1, imported_functions2 = None, None
    exported_functions1, exported_functions2 = None, None
    strings1, strings2 = get_strings(file1), get_strings(file2)
    if binary1:
        h1 = binary1.header
        lib1 = binary1.libraries
        imported_functions1 = [function.name for function in binary1.imported_functions]
        exported_functions1 = [function.name for function in binary1.exported_functions]
        strings1 = binary1.get_strings()
    if binary2:
        h2 = binary2.header
        lib2 = binary2.libraries
        imported_functions2 = [function.name for function in binary2.imported_functions]
        exported_functions2 = [function.name for function in binary2.exported_functions]
        strings2 = binary2.get_strings()
    if h1 and h2:
        h1, h2 = get_header_diff(h1, h2)
    lib1, lib2 = get_unique_sets(lib1, lib2)
    imported_functions1, imported_functions2 = get_unique_sets(imported_functions1, imported_functions2)
    exported_functions1, exported_functions2 = get_unique_sets(exported_functions1, exported_functions2)
    strings1, strings2 = get_unique_sets(strings1, strings2)
    elf1 = ELF(h1, lib1, imported_functions1, exported_functions1, strings1)
    elf2 = ELF(h2, lib2, imported_functions2, exported_functions2, strings2)
    return elf1, elf2


def get_strings(file):
    try:
        return file.decode().splitlines()
    except UnicodeDecodeError:
        return None


def get_header_diff(head1, head2):
    template = ['Class:',
                'Endianness:',
                'Version:',
                'OS/ABI::',
                'ABI Version:',
                'Machine type:',
                'File type:',
                'Object file version:',
                'Entry Point:',
                'Program header offset:',
                'Section header offset:',
                'Processor Flag:',
                'Header size:',
                'Size of program header:',
                'Number of program header:',
                'Size of section header:',
                'Number of section headers:',
                'Section Name Table idx:']
    mapping = [6, 8, 10, 12, 15, 18, 21, 25, 28, 32, 36, 39, 42, 48, 53, 58, 63, 68]  
    h1 = head1.__str__().split()
    h2 = head2.__str__().split()
    magic1 = ''.join(h1[1:5])
    magic2 = ''.join(h2[1:5])
    if magic1 == magic2:
        out1 = '<li><span style="background-color:#008000">Magic:{}</span></li>'.format(magic1)
        out2 = '<li><span style="background-color:#008000">Magic:{}</span></li>'.format(magic2)
    else:
        out1 = '<li>Magic:{}</li>'.format(magic1)
        out2 = '<li>Magic:{}</li>'.format(magic2)
    for index, string in enumerate(template):
        if h1[mapping[index]] == h2[mapping[index]]:
            out1 += '<li><span style="background-color:#008000">{}{}</span></li>'.format(string, h1[mapping[index]])
            out2 += '<li><span style="background-color:#008000">{}{}</span></li>'.format(string, h2[mapping[index]])
        else:
            out1 += '<li>{}{}</li>'.format(string, h1[mapping[index]])
            out2 += '<li>{}{}</li>'.format(string, h2[mapping[index]])
    return out1, out2
        
           
def get_unique_sets(list1, list2):
    if list1 and list2:
        set1 = set(list1)
        set2 = set(list2)
        list1 = set1 - set2
        list2 = set2 - set1
    return list1, list2
