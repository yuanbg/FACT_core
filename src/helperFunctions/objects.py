
def get_root_of_virtual_path(virtual_path):
    return virtual_path.split("|")[0]


def get_base_of_virtual_path(virtual_path):
    return "|".join(virtual_path.split("|")[:-1])


def get_top_of_virtual_path(virtual_path):
    return virtual_path.split("|")[-1]
