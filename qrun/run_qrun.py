import subprocess
import time
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
def run_qrun_with_delay(config_file, delay_seconds=0.1):
    """
    运行 qrun 命令，可以设置每次运行之间的延迟

    参数:
        config_file: 配置文件名
        delay_seconds: 每次运行后的延迟秒数
    """
    cmd = f"qrun {config_file}"

    print(f"执行命令: {cmd}")
    print(f"运行后延迟: {delay_seconds} 秒")
    print("=" * 50)

    result = subprocess.run(cmd, shell=True)

    print("=" * 50)
    print(f"命令执行完成，返回码: {result.returncode}")

    if result.returncode == 0:
        print("回测成功完成！")
    else:
        print("回测执行过程中出现错误")

    if delay_seconds > 0:
        print(f"等待 {delay_seconds} 秒...")
        time.sleep(delay_seconds)

    return result.returncode

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="运行 qrun 并添加延迟")
    parser.add_argument("-f", "--file", default="qrun/config_qrun.yaml", help="配置文件名")
    parser.add_argument("-d", "--delay", type=float, default=0.1, help="延迟秒数")

    args = parser.parse_args()

    run_qrun_with_delay(config_file=args.file, delay_seconds=args.delay)

