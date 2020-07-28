import logging

from intercom.common_mongo_binding import InterComDispatcher, InterComListener


class InterComFrontEndDispatcher(InterComDispatcher):
    '''
    Internal Communication Frontend Dispatcher
    receives requests from the backend through the intercom and dispatches them
    '''
    def __init__(self, config, testing=False):
        super().__init__(config)
        if not testing:
            self.startup()
        logging.info('InterCom FrontEnd Dispatcher started')

    def startup(self):
        self.start_webhook_listener()

    def start_webhook_listener(self):
        self._start_listener(InterComFrontEndWebhookTask)


class InterComFrontEndWebhookTask(InterComListener):

    CONNECTION_TYPE = 'web_hook_task'

    def post_processing(self, task, task_id):
        # TODO: send webhook message here; task = url, task_id = uid
        return task
