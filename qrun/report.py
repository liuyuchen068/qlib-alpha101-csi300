import pandas as pd
# 文件路径（使用原始字符串避免转义问题）
file_path = r"C:\Users\ASUS\Desktop\my-project\data\results_qrun\256292353796231490\17e68b9f2daa4c8b9124bdd40a3db59f\artifacts\portfolio_analysis\report_normal_1day.pkl"
# 文件为 pandas DataFrame
df = pd.read_pickle(file_path)
# 检查是否确实是 DataFrame
if isinstance(df, pd.DataFrame):
    df.to_csv(r"C:\Users\ASUS\Desktop\my-project\data\results_qrun\report.csv", index=False)
    print("成功转换为 CSV，文件保存为 report.csv")
else:
    print("读取的对象不是 DataFrame，类型为：", type(df))
