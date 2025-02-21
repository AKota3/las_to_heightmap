import subprocess
from pymongo import MongoClient
import gridfs
from PIL import Image
import io
import os
import csv
from datetime import datetime

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
    "docker", "run", "--name", "las2heightmap_container", "--rm",  # コンテナ名を指定
    "-v", f"{current_dir}:/data",  # 現在のディレクトリを絶対パスで指定
    "las2heightmap", "-i", input_file, "-o", output_file, 
    "-W", str(width), "-H", str(height),
    "-elevation_csv", csv_file,  # 標高データをCSVとして出力
]

# subprocess でコマンドを実行
try:
    subprocess.run(command, check=True)
    print(f"las2heightmap executed successfully. Output saved to {output_file}")
except subprocess.CalledProcessError as e:
    print(f"Error occurred while running las2heightmap: {e}")
    exit(1)

'''
# 2. DockerコンテナIDを取得する
get_container_id_command = [
    "docker", "ps", "-q", "-f", "name=las2heightmap_container"  # 指定したコンテナ名でフィルタ
]
'''
'''
try:
    container_id = subprocess.check_output(get_container_id_command).decode("utf-8").strip()
    if not container_id:
        raise Exception("Docker container not found.")
    print(f"Docker container ID: {container_id}")
except subprocess.CalledProcessError as e:
    print(f"Error occurred while retrieving container ID: {e}")
    exit(1)

# 3. Docker内のCSVファイルをローカルに保存する
csv_local_path = os.path.join(current_dir, 'elevation_min_max.csv')

# docker cp コマンドでコンテナからローカルにファイルをコピー
try:
    docker_cp_command = [
        "docker", "cp", f"{container_id}:{csv_file}", f"{csv_local_path}"
    ]
    subprocess.run(docker_cp_command, check=True)
    print(f"CSVファイルをDockerコンテナからローカルにコピーしました: {csv_local_path}")
except subprocess.CalledProcessError as e:
    print(f"Error occurred while copying CSV file from Docker: {e}")
    exit(1)

'''
# 4. chmod を実行してパーミッションを変更
chmod_command = [
    "docker", "run", "--rm",
    "-v", f"{current_dir}:/data",  # 現在のディレクトリを絶対パスで指定
    "busybox", "chmod", "644", "/data/outputTest.png"  # busyboxを使ってchmodを実行
]

# CSVファイルのパーミッション変更
chmod_command_csv = [
    "docker", "run", "--rm",
    "-v", f"{current_dir}:/data",  # 現在のディレクトリを絶対パスで指定
    "busybox", "chmod", "644", "/data/elevation_min_max.csv"  # CSVファイルのパーミッションを変更
]

# subprocess で chmod を実行
try:
    subprocess.run(chmod_command, check=True)
    print(f"Permissions of {output_file} changed successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error occurred while changing permissions: {e}")
    exit(1)


# CSVファイルのchmodを実行
try:
    subprocess.run(chmod_command_csv, check=True)
    print(f"Permissions of {csv_file} changed successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error occurred while changing permissions for the CSV: {e}")
    exit(1)

output_file = os.path.join(current_dir, 'outputTest.png')

##################
# CSVファイルのパス
#csv_file_path = '/data/elevation_min_max.csv'
csv_file_path = os.path.join(current_dir, 'elevation_min_max.csv')

# CSVファイルを開いて読み込む
def read_csv(csv_file_path):
    with open(csv_file_path, mode='r') as file:
        csv_reader = csv.reader(file)
        headers = next(csv_reader)  # ヘッダー行をスキップ
        for row in csv_reader:
            # 行ごとにデータを処理
            min_x, max_x, min_y, max_y, min_z, max_z = row
            print("reading csv")
            print(f"minX: {min_x}, maxX: {max_x}, minY: {min_y}, maxY: {max_y}, minZ: {min_z}, maxZ: {max_z}")
            return min_x, max_x, min_y, max_y, min_z, max_z  # 必要な値を返す

# CSVファイルを読み込む
min_x, max_x, min_y, max_y, min_z, max_z = read_csv(csv_file_path)
######################
# 現在の時刻を取得
upload_time = datetime.now()
StDytype = 'static'
DataId = 4031
DataHeight = float(max_x) - float(min_x)
DataWidth = float(max_y) - float(min_y)
DataElevation = float(max_z) - float(min_z)
DataKinds = 'heightmap'


# 5. 画像ファイルを MongoDB に保存
try:
    with open(output_file, 'rb') as f:
        image_data = f.read()

        # 画像データを GridFS に保存
        fs.put(f.read(), filename=os.path.basename(output_file), time=upload_time , type=StDytype, id=DataId, height=DataHeight, width=DataWidth, elevation=DataElevation, offset_x = 00, offset_y = 00, DataType=DataKinds)

   # file_id = fs.put(image_data, filename='outputTest.png')
   # print(f"画像ファイルは MongoDB に保存されました。ファイルID: {file_id}")
except Exception as e:
    print(f"Error occurred while saving image to MongoDB: {e}")
    exit(1)





