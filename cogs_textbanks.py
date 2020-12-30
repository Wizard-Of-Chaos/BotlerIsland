# Bot text bank
import re
import random
import functools
from typing import Callable

from data_urls import urls
from data_responses import (
    queries, quirked_responses, unquirked_responses, apply_quirk
    )

class AttrDict(dict):
    def __getitem__(self, item: str) -> str:
        return super().__getitem__(item)

    __getattr__ = __getitem__

class ResponseBank(AttrDict):
    __slots__ = ('quirk_func',)

    def __init__(self, qresps: dict, uresps: dict, quirk_func: Callable[[str], str]) -> None:
        quirk_func = self._quirk_wrapper(quirk_func)
        super().__init__(uresps)
        self.quirk_func = quirk_func
        for resp_id, resp in qresps.items():
            if isinstance(resp, str):
                self[resp_id] = quirk_func(resp)
            else:
                self[resp_id] = tuple(map(quirk_func, resp))

    def __getitem__(self, resp_id: str) -> str:
        resp = super().__getitem__(resp_id)
        return resp if isinstance(resp, str) else random.choice(resp)

    @staticmethod
    def _quirk_wrapper(quirk_func: Callable[[str], str]) -> Callable[[str], str]:
        @functools.wraps(quirk_func)
        def _wrapped_quirk(resp: str) -> str:
            args = []
            while (match := re.search(r'{.+?}', resp)):
                resp = f'{resp[:match.start(0)]}\\{len(args)}{resp[match.end(0):]}'
                args.append(match[0])
            resp = quirk_func(resp)
            return re.sub(r'\\\d+', lambda m: args[int(m[0][1:])], resp)
        return _wrapped_quirk

url_bank = AttrDict(urls)
query_bank = AttrDict(queries)
response_bank = ResponseBank(quirked_responses, unquirked_responses, apply_quirk)
