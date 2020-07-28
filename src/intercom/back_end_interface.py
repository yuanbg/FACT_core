import pickle

from intercom.common_mongo_binding import InterComMongoInterface


class InterComBackEndInterface(InterComMongoInterface):
    '''
    Internal Communication BackEnd Interface
    sends requests from the backend through the intercom to the frontend dispatcher
    '''

    def send_webhook_message(self, url: str, uid: str):
        self.connections['web_hook_task']['fs'].put(pickle.dumps(url), filename=uid)
