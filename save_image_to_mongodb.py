import subprocess
from pymongo import MongoClient
import gridfs
from PIL import Image
import io
import os

# MongoDB に接続
client = MongoClient('mongodb://localhost:27017/')  # MongoDB がローカルにある場合
db = client['heightmap_db']  # データベース名
fs = gridfs.GridFS(db)  # GridFS の初期化

# 入力ファイルと出力ファイルのパス
input_file = '/data/1120PM_after_cut.las'
output_file = '/data/outputTest.png'
width = 2048
height = 2048

csv_file = '/data/elevation_min_max.csv'
# 現在の作業ディレクトリを取得
current_dir = os.getcwd()

# 1. las2heightmap を実行して画像を生成
command = [
    "docker", "run", "--rm",
    "-v", f"{current_dir}:/data",  # 現在のディレクトリを絶対パスで指定
    "las2heightmap", "-i", input_file, "-o", output_file, 
    "-W", str(width), "-H", str(height),
    "-elevation_csv", csv_file  # 標高データをCSVとして出力
]

# subprocess でコマンドを実行
try:
    subprocess.run(command, check=True)
    print(f"las2heightmap executed successfully. Output saved to {output_file}")
except subprocess.CalledProcessError as e:
    print(f"Error occurred while running las2heightmap: {e}")
    exit(1)

# 2. chmod を実行してパーミッションを変更
chmod_command = [
    "docker", "run", "--rm",
    "-v", f"{current_dir}:/data",  # 現在のディレクトリを絶対パスで指定
    "busybox", "chmod", "644", "/data/outputTest.png"  # busyboxを使ってchmodを実行
]

# subprocess で chmod を実行
try:
    subprocess.run(chmod_command, check=True)
    print(f"Permissions of {output_file} changed successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error occurred while changing permissions: {e}")
    exit(1)

output_file = os.path.join(current_dir, 'outputTest.png')


# 2. 画像ファイルを MongoDB に保存
try:
    with open(output_file, 'rb') as f:
        image_data = f.read()

    # 画像データを GridFS に保存
    file_id = fs.put(image_data, filename='outputTest.png')
    print(f"画像ファイルは MongoDB に保存されました。ファイルID: {file_id}")
except Exception as e:
    print(f"Error occurred while saving image to MongoDB: {e}")
    exit(1)

# MongoDB に CSV ファイルを保存するコード
csv_file = os.path.join(current_dir, 'elevation_min_max.csv')

# CSV ファイルを MongoDB に保存
try:
    with open(csv_file, 'rb') as f:
        csv_data = f.read()

    # CSV データを GridFS に保存
    csv_file_id = fs.put(csv_data, filename='elevation_min_max.csv')
    print(f"CSVファイルは MongoDB に保存されました。ファイルID: {csv_file_id}")
except Exception as e:
    print(f"Error occurred while saving CSV to MongoDB: {e}")
    exit(1)
