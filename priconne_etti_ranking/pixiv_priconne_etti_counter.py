import os
import time
import csv
from typing import Any, Final, NamedTuple, Union
from pixivpy3 import AppPixivAPI
from pixivpy3.utils import PixivError
from princesses import PRINCESSES


class ResultData(NamedTuple):
    name: str
    all_illust_num: int
    etti_illust_num: int
    etti_rate: float


class PixivEttiCounter(object):
    def __init__(self):
        self.__ACCESS_INTERVAL: Final[float] = 1    # sec
        self.__GET_ILLUST_RETRY_NUM: Final[int] = 100
        self.__NEXT_ILLUST_RETRY_NUM: Final[int] = 10

        self.__api: AppPixivAPI = AppPixivAPI()
        try:
            self.__api.login(os.environ["PIXIV_ID"], os.environ["PIXIV_PASSWORD"])
        except PixivError as e:
            print(e)

    def __get_illusts(self, tag: str) -> Union[Any, None]:
        # NOTE: この関数もうちょっとスマートにならないものか……
        illusts: list = []
        # 初回
        json_result: Any = self.__api.search_illust(tag)
        if json_result.illusts is None:
            print("error: no illusts.")
            return None
        for illust in json_result.illusts:
            illusts.append(illust)
        count: int = 1
        # 次以降
        next_qs = self.__api.parse_qs(json_result.next_url)
        try_count: int = 0
        while next_qs is not None:
            json_result: Any = self.__api.search_illust(**next_qs)
            if json_result.illusts is None:
                if try_count > self.__NEXT_ILLUST_RETRY_NUM:
                    break
                if try_count != 0 and try_count % 10 == 0:
                    print("wait a minutes...")
                    time.sleep(60)
                try_count = try_count + 1
                continue
            for illust in json_result.illusts:
                illusts.append(illust)
            next_qs: Any = self.__api.parse_qs(json_result.next_url)
            time.sleep(self.__ACCESS_INTERVAL)
        print("got " + str(count) + " pages.")
        return illusts

    # NOTE: is princessとis ettiで2回ループが回るので効率が悪い
    def __is_princess(self, illust: Any) -> bool:
        return True     # NOTE: 結果が多すぎるとうまく行かない。検索タグに(プリコネ)を極力つけることで妥協した……
        for tag in illust["tags"]:
            if "プリンセスコネクト!Re:Dive" in tag["name"]:
                return True
            if "プリコネ" in tag["name"]:
                return True
            if "PrincessConnect" in tag["name"]:
                return True
        return False

    def __is_etti(self, illust: Any) -> bool:
        for tag in illust["tags"]:
            if tag["name"] == "R-18":
                return True
        return False

    def __count_all_princess(self, illusts: Any) -> int:
        count: int = 0
        for illust in illusts:
            if self.__is_princess(illust):
                count = count + 1
        print("all princess : " + str(count))
        return count

    def __count_etti_princess(self, illusts: Any) -> int:
        count: int = 0
        for illust in illusts:
            if self.__is_princess(illust) and self.__is_etti(illust):
                count = count + 1
        print("etti princess : " + str(count))
        return count

    def __calculate(self, name: str) -> Union[ResultData, None]:
        try_count: int = 0
        illusts: Any = None
        while try_count < self.__GET_ILLUST_RETRY_NUM:
            illusts = self.__get_illusts(name)
            if illusts is not None:
                break
            print("Failed to get " + name + " data. Retrying...")
            print("wait a minutes...")
            time.sleep(60)
            try_count = try_count + 1
        if illusts is None:
            print("Failed to get " + name + " data. Skip her.")
            return None
        all_num: int = self.__count_all_princess(illusts)
        etti_num: int = self.__count_etti_princess(illusts)
        etti_rate: float = etti_num / all_num
        result = ResultData(
            name=name,
            all_illust_num=all_num,
            etti_illust_num=etti_num,
            etti_rate=etti_rate
        )
        return result

    def __print_result(self, result: ResultData):
        print("name,all_illust_num,etti_illust_num,etti_rate")
        print(result.name + "," + str(result.all_illust_num) + "," + str(result.etti_illust_num) + "," + str(result.etti_rate))

    def __write_result(self, results: list[ResultData]):
        # NOTE: 全部まとめて書き出すので、途中で失敗すると何も出力されない
        with open("./result.csv", "w") as f:
            writer: Any = csv.writer(f)
            writer.writerow(["name", "all_illust_num", "etti_illust_num", "etti_rate"])
            for result in results:
                result_row = [result.name, result.all_illust_num, result.etti_illust_num, result.etti_rate]
                writer.writerow(result_row)

    def execute(self):
        results: list[ResultData] = []
        print("start etti rate calculation...")
        for princess in PRINCESSES:
            print("calculating " + princess + " etti rate...")
            result = self.__calculate(princess)
            if result is None:
                print("skip " + princess)
                continue
            self.__print_result(result)
            results.append(result)
        self.__write_result(results)
        print("etti rate calculation is ended.")

if __name__ == '__main__':
    etti_counter: PixivEttiCounter = PixivEttiCounter()
    etti_counter.execute()

# これ使ってタグ付けうまくいってないえっちイラスト発掘できそう
