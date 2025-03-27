import laspy

# LASファイルを読み込む
las = laspy.read('CollageWeb.las')  # 'path_to_your_file.las' を実際のファイルパスに置き換えてください

# X, Y, Zの座標を取得
x = las.x
y = las.y
z = las.z

# 最大値と最小値を計算
x_min, x_max = x.min(), x.max()
y_min, y_max = y.min(), y.max()
z_min, z_max = z.min(), z.max()

# 結果を表示
print(f"X座標の最小値: {x_min}, 最大値: {x_max}")
print(f"Y座標の最小値: {y_min}, 最大値: {y_max}")
print(f"Z座標の最小値: {z_min}, 最大値: {z_max}")
