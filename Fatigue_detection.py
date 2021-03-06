#导入工具包
from scipy.spatial import distance as dist
from collections import OrderedDict
import numpy as np
import argparse
import time
import dlib
import cv2

# 创建集合
FACIAL_LANDMARKS_68_IDXS = OrderedDict([
	("mouth", (48, 68)),
	("right_eyebrow", (17, 22)),
	("left_eyebrow", (22, 27)),
	("right_eye", (36, 42)),
	("left_eye", (42, 48)),
	("nose", (27, 36)),
	("jaw", (0, 17))
])


# 计算眼睛的EAR函数
def eye_aspect_ratio(eye):
	# 计算距离，竖直的
	A = dist.euclidean(eye[1], eye[5])
	B = dist.euclidean(eye[2], eye[4])
	# 计算距离，水平的
	C = dist.euclidean(eye[0], eye[3])
	# ear值
	ear = (A + B) / (2.0 * C)
	return ear
# 计算嘴巴的MAR函数
def mouse_aspect_ratio(mouth):
	# 计算距离，竖直的
	A = dist.euclidean(mouth[2], mouth[10])
	B = dist.euclidean(mouth[4], mouth[8])
	# 计算距离，水平的
	C = dist.euclidean(mouth[0], mouth[6])
	# mar值
	mar = (A + B) / (2.0 * C)
	return mar

# 输入参数
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--shape-predictor", required=True,
	help="path to facial landmark predictor")
ap.add_argument("-v", "--video", type=str, default="",
	help="path to input video file")
args = vars(ap.parse_args())
 
# 设置判断参数
# 眨眼
EYE_AR_THRESH = 0.2
EYE_AR_CONSEC_FRAMES = 3
# 打哈欠
MAR_THRESH = 0.8
MOUTH_AR_CONSEC_FRAMES = 5

# 初始化计数器
COUNTER1 = 0
TOTAL1 = 0
COUNTER2 = 0
TOTAL2 = 0

# 检测与定位工具
print("[INFO] loading facial landmark predictor...")
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(args["shape_predictor"])

# 分别取两个眼睛和嘴巴区域
(lStart, lEnd) = FACIAL_LANDMARKS_68_IDXS["left_eye"]
(rStart, rEnd) = FACIAL_LANDMARKS_68_IDXS["right_eye"]
(mStart, mEnd) = FACIAL_LANDMARKS_68_IDXS["mouth"]

# 读取视频
print("[INFO] starting video stream thread...")
vs = cv2.VideoCapture(args["video"])
#vs = FileVideoStream(args["video"]).start()
time.sleep(1.0)

def shape_to_np(shape, dtype="int"):
	# 创建68*2
	coords = np.zeros((shape.num_parts, 2), dtype=dtype)
	# 遍历每一个关键点
	# 得到坐标
	for i in range(0, shape.num_parts):
		coords[i] = (shape.part(i).x, shape.part(i).y)
	return coords

# 遍历每一帧
while True:
	# 预处理
	frame = vs.read()[1]
	if frame is None:
		break
	
	(h, w) = frame.shape[:2]
	width=1200
	r = width / float(w)
	dim = (width, int(h * r))
	frame = cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

	# 检测人脸
	rects = detector(gray, 0)

	# 遍历每一个检测到的人脸
	for rect in rects:
		# 获取坐标
		shape = predictor(gray, rect)
		shape = shape_to_np(shape)

		# 分别计算ear值
		leftEye = shape[lStart:lEnd]
		rightEye = shape[rStart:rEnd]
		leftEAR = eye_aspect_ratio(leftEye)
		rightEAR = eye_aspect_ratio(rightEye)

		# 算一个平均的
		ear = (leftEAR + rightEAR) / 2.0

		# 绘制眼睛区域
		leftEyeHull = cv2.convexHull(leftEye)
		rightEyeHull = cv2.convexHull(rightEye)
		cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
		cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)

		# 计算嘴巴mar值
		Mouth = shape[mStart:mEnd]
		mar = mouse_aspect_ratio(Mouth)

		# 绘制嘴巴区域
		MOUTH = cv2.convexHull(Mouth)
		cv2.drawContours(frame, [MOUTH], -1, (0, 255, 0), 1)

		# 眨眼检查是否满足阈值
		if ear < EYE_AR_THRESH:
			COUNTER1 += 1

		else:
			# 如果连续几帧都是闭眼的，总数算一次
			if COUNTER1 >= EYE_AR_CONSEC_FRAMES:
				TOTAL1 += 1

			# 重置
			COUNTER1 = 0

		# 嘴巴检查是否满足阈值
		if mar < MAR_THRESH:
			COUNTER2 += 1

		else:
			# 如果连续几帧都是张嘴的，总数算一次
			if COUNTER2 >= MOUTH_AR_CONSEC_FRAMES:
				TOTAL2 += 1

			# 重置
			COUNTER2 = 0

		# 显示
		# 眨眼
		cv2.putText(frame, "Blink: {}".format(TOTAL1), (10, 30),
			cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
		cv2.putText(frame, "EAR: {:.2f}".format(ear), (10, 70),
			cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
		# 打哈欠
		cv2.putText(frame, "Yawning: {}".format(TOTAL2), (150, 30),
					cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
		cv2.putText(frame, "MAR: {:.2f}".format(mar), (150, 70),
					cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

	cv2.imshow("Frame", frame)
	key = cv2.waitKey(1) & 0xFF
 
	if key == 27:
		break

vs.release()
cv2.destroyAllWindows()