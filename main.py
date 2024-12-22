import sys
import cv2
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMessageBox
from ui_main import Ui_MainWindow  # 确保 ui_main.py 文件已生成并正确导入

# 覆盖图像函数
def overlay_img(img, img_over, img_over_x, img_over_y):
    h, w = img_over.shape[:2]
    for i in range(h):
        for j in range(w):
            if img_over[i, j, 3] > 0:  # 检查 alpha 通道
                alpha = img_over[i, j, 3] / 255.0
                for c in range(3):  # BGR 通道
                    img[img_over_y + i, img_over_x + j, c] = (1 - alpha) * img[img_over_y + i, img_over_x + j, c] + alpha * img_over[i, j, c]
    return img

class MainCall(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainCall, self).__init__(parent)
        self.setupUi(self)  # 加载 UI
        self.CAM_NUM = 0
        self.cap = cv2.VideoCapture(2)
        self.ACQ_FRAME_Flag = 0  # 0-不获取一帧影像,1-获取一帧影像
        self.current_frame = None  # 用于保存当前帧
        self.background()
        self.init_timer()

    # 控件初始化方法
    def background(self):
        self.pushButton_openCamera.clicked.connect(self.open_camera)  # 打开摄像头按钮
        self.pushButton_closeCamera.clicked.connect(self.close_camera)  # 关闭摄像头按钮
        self.pushButton_saveFrame.clicked.connect(self.save_frame)  # 保存帧按钮
        self.pushButton_openCamera.setEnabled(True)
        self.pushButton_closeCamera.setEnabled(False)
        self.pushButton_saveFrame.setEnabled(False)  # 初始状态下禁用保存按钮

    # 摄像头打开方法
    def open_camera(self):
        index = self.comboBox_cameraSelect.currentIndex()  # 获取选择的摄像头
        print(index)
        self.CAM_NUM = index
        flag = self.cap.open(self.CAM_NUM)
        print(flag)
        if not flag:
            QMessageBox.information(self, "警告", "该设备未正常连接", QMessageBox.Ok)
        else:
            self.label_camera.setEnabled(True)  # 显示原始视频的标签
            self.label_processed.setEnabled(True)  # 显示处理后视频的标签
            self.pushButton_openCamera.setEnabled(False)
            self.pushButton_closeCamera.setEnabled(True)
            self.pushButton_saveFrame.setEnabled(True)  # 开启保存按钮
            self.timer.start()
            print("beginning!")

    # 摄像头关闭方法
    def close_camera(self):
        self.cap.release()
        self.pushButton_openCamera.setEnabled(True)
        self.pushButton_closeCamera.setEnabled(False)
        self.pushButton_saveFrame.setEnabled(False)  # 关闭保存按钮
        self.timer.stop()

    # 定时器方法
    def init_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.show_pic)

    # 视频显示方法
    def show_pic(self):
        ret, img = self.cap.read()
        if ret:
            cur_frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            height, width = cur_frame.shape[:2]
            # 不带特效的视频
            pixmap = QImage(cur_frame, width, height, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(pixmap)
            ratio = max(width / self.label_camera.width(), height / self.label_camera.height())
            pixmap.setDevicePixelRatio(ratio)
            self.label_camera.setAlignment(Qt.AlignCenter)
            self.label_camera.setPixmap(pixmap)

            # 带特效的视频
            processed_frame = self.process_face_video(cur_frame)
            q_img = QImage(processed_frame, width, height, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            ratio = max(width / self.label_processed.width(), height / self.label_processed.height())
            pixmap.setDevicePixelRatio(ratio)
            self.label_processed.setAlignment(Qt.AlignCenter)
            self.label_processed.setPixmap(pixmap)
            self.current_frame = processed_frame  # 保存当前处理后的帧
            self.show_acqframe(pixmap)  # 显示截取的图片
        else:
            self.label_camera.setText("未打开摄像头")
            self.label_processed.setText("未打开摄像头")

    # 获取一帧影像的方法
    def acqframe(self):
        self.ACQ_FRAME_Flag = 1

    # 子函数show_acqframe
    def show_acqframe(self, pixmap):
        if self.ACQ_FRAME_Flag == 1:
            self.label_2.setAlignment(Qt.AlignCenter)
            self.label_2.setPixmap(pixmap)
            self.ACQ_FRAME_Flag = 0

    # 处理带有人脸检测的视频
    def process_face_video(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, 1.2, 5)
        for (x, y, w, h) in faces:
            print(f"Face detected at ({x}, {y}) with size ({w}, {h})")
            glass_img = cv2.imread("glass.png", cv2.IMREAD_UNCHANGED)
            if glass_img is None:
                print("Failed to load glass.png")
                continue
            height, width, channel = glass_img.shape
            gw = w
            gh = int(height * w / width)
            print(f"Resized glass image to ({gw}, {gh})")
            glass_img = cv2.resize(glass_img, (gw, gh))
            frame = overlay_img(frame, glass_img, x, y + int(h * 1 / 3))
        return frame

    # 保存当前帧到本地
    def save_frame(self):
        if self.current_frame is not None:
            file_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存图片", "", "Images (*.png *.xpm *.jpg *.bmp *.gif)")
            if file_name:
                cv2.imwrite(file_name, cv2.cvtColor(self.current_frame, cv2.COLOR_RGB2BGR))
                QMessageBox.information(self, "提示", f"图片已保存到 {file_name}", QMessageBox.Ok)
        else:
            QMessageBox.warning(self, "警告", "没有可保存的图片", QMessageBox.Ok)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mywindow = MainCall()
    mywindow.show()
    sys.exit(app.exec_())
