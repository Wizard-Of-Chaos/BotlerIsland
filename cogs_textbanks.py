# Bot text bank
import re
import random
import functools
from typing import Callable

from data_responses import (
    queries, quirked_responses, unquirked_responses, apply_quirk
    )

class QueryBank(dict):
    def __getitem__(self, item: str) -> str:
        return super().__getitem__(item)

    __getattr__ = __getitem__

class ResponseBank(dict):
    __slots__ = ('quirk_func',)

    def __init__(self, qres: dict, uqres: dict, quirk_func: Callable[[str], str]) -> None:
        quirk_func = self._quirk_wrapper(quirk_func)
        super().__init__()
        self.quirk_func = quirk_func
        self.update(uqres)
        for res_id, res in qres.items():
            if isinstance(res, tuple):
                super().__setitem__(res_id, tuple(map(self.quirk_func, res)))
            else:
                super().__setitem__(res_id, self.quirk_func(res))

    def __getitem__(self, res_id: str) -> str:
        res = super().__getitem__(res_id)
        if isinstance(res, tuple):
            return random.choice(res)
        else:
            return res

    __getattr__ = __getitem__

    @staticmethod
    def _quirk_wrapper(quirk_func: Callable[[str], str]) -> Callable[[str], str]:
        @functools.wraps(quirk_func)
        def wrapped(response: str) -> str:
            args = []
            while (match := re.search(r'{.+?}', response)):
                response = f'{response[:match.start(0)]}\\{len(args)}{response[match.end(0):]}'
                args.append(match[0])
            response = quirk_func(response)
            return re.sub(
                r'\\\d+',
                lambda m: args[int(m[0][1:])],
                response,
                )
        return wrapped

query_bank = QueryBank(queries)
response_bank = ResponseBank(quirked_responses, unquirked_responses, apply_quirk)
