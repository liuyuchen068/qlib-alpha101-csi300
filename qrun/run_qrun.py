"""
qrun 启动器
用于执行 Qlib 工作流配置，并支持设置延迟防止程序崩溃

使用方法:
    python run_qrun.py                    # 使用默认配置
    python run_qrun.py -f config.yaml     # 指定配置文件
    python run_qrun.py -d 0.5            # 设置延迟 0.5 秒
"""
import subprocess
import time
import os

# 限制线程数，防止 LightGBM 和 Numpy 过度并行导致内存问题
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"


def run_qrun_with_delay(config_file: str, delay_seconds: float = 0.1) -> int:
    """
    运行 qrun 命令，可以设置每次运行之间的延迟

    参数:
        config_file: Qlib 配置文件名（如 'config_qrun.yaml'）
        delay_seconds: 每次运行后的延迟秒数，用于防止程序崩溃

    返回:
        返回码（0 表示成功，非 0 表示失败）
    """
    # 构建 qrun 命令
    cmd = f"qrun {config_file}"

    # 打印启动信息
    print(f"执行命令: {cmd}")
    print(f"运行后延迟: {delay_seconds} 秒")
    print("=" * 50)

    # 执行命令，shell=True 让命令在 shell 中解释
    result = subprocess.run(cmd, shell=True)

    print("=" * 50)
    print(f"命令执行完成，返回码: {result.returncode}")

    # 根据返回码判断执行结果
    if result.returncode == 0:
        print("回测成功完成！")
    else:
        print("回测执行过程中出现错误")

    # 如果设置了延迟，等待一段时间
    if delay_seconds > 0:
        print(f"等待 {delay_seconds} 秒...")
        time.sleep(delay_seconds)

    return result.returncode


if __name__ == "__main__":
    import argparse

    # 命令行参数解析
    parser = argparse.ArgumentParser(description="运行 qrun 并添加延迟")
    
    # -f/--file: 配置文件名，默认 'qrun/config_qrun.yaml'
    parser.add_argument("-f", "--file", default="qrun/config_qrun.yaml", help="配置文件名")
    
    # -d/--delay: 延迟秒数，默认 0.1 秒
    parser.add_argument("-d", "--delay", type=float, default=0.1, help="延迟秒数")

    # 解析命令行参数
    args = parser.parse_args()

    # 调用主函数
    run_qrun_with_delay(config_file=args.file, delay_seconds=args.delay)

