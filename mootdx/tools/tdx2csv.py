import asyncio
import glob
from functools import partial
from pathlib import Path

import pandas as pd

from mootdx.logger import logger


def txt2csv(infile: str, outfile: str = None) -> pd.DataFrame:
    """通达信导出文件转换为 Pandas 可用的 csv 文件

    :param infile: 通达信导出的 txt 文件路径
    :param outfile: 转换后的目标 csv 文件路径
    """

    try:
        names = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
        df = pd.read_csv(infile, names=names, header=2, skipfooter=1, index_col='date', engine='python', encoding='gbk')

        # 传参 outfile 目录存在则写文件
        outfile = outfile if outfile else infile.replace('.txt', '.csv')
        Path(outfile).parent.is_dir() and df.to_csv(outfile)

        return df
    except FileNotFoundError as ex:
        logger.error(f'输入文件不存在: {infile}')
        return pd.DataFrame(None)
    except (ValueError, TypeError) as ex:
        logger.error(f'无法解析输入文件: {infile}')
        return pd.DataFrame(None)


async def covert(src, dst):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(txt2csv, infile=src, outfile=dst))


def batch(src, dst):
    """批量转换通达信导出文件

    :param src: 来源目录
    :param dst: 目标目录
    """

    async def convert_all():
        tasks = []

        # 分配任务
        for x in glob.glob1(src, '*.txt'):
            src_ = str(Path(src, x))
            dst_ = src_.replace('.txt', '.csv')
            tasks.append(covert(src=src_, dst=dst_))

        # 执行任务
        return await asyncio.gather(*tasks)

    return asyncio.run(convert_all())


__all__ = ('txt2csv', 'batch')
