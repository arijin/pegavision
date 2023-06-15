import os
import json

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QBrush
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QSlider, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox

from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QSplitter, QInputDialog, QScrollArea, QTreeWidget, QTreeWidgetItem
# from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QDialog, QRadioButton, QButtonGroup, QTextEdit

from PyQt5.QtWidgets import QLabel, QRadioButton, QVBoxLayout, QPushButton, QDialog, QButtonGroup, QGridLayout

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
from module import CLIP, BBOX

class RadioButtonDialog(QDialog):
    def __init__(self, class_ids, current_class_id, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Select Class ID")
        layout = QGridLayout()

        self.button_group = QButtonGroup(self)

        self.colors = {
            "green": "green",
            "red": "red",
            "yellow": "#FFE933",
            "black": "black",
            "green_blink": "green",
            "red_blink": "red",
            "yellow_blink": "#FFE933",
            "unknown": "gray"
        }

        max_items_per_row = 4  # 每行最多放置4个选项
        row = 0
        col = 0

        for class_id, class_name in class_ids.items():
            radio_button = QRadioButton("")
            self.button_group.addButton(radio_button, class_id)
            layout.addWidget(radio_button, row, col * 2)

            if "_blink" in class_name:
                color, blink_text = class_name.split('_')
                colored_text = f'<span style="color:{self.colors[color]};">{color}</span><span style="color:orange;">_{blink_text}</span>'
            else:
                colored_text = f'<span style="color:{self.colors[class_name]};">{class_name}</span>'

            label = QLabel(f'<span style="color:black;">{class_id}:</span> {colored_text}')
            layout.addWidget(label, row, col * 2 + 1)

            if class_id == current_class_id:
                radio_button.setChecked(True)

            col += 1
            if col == max_items_per_row:
                col = 0
                row += 1

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button, row + 1, 0, 1, max_items_per_row * 2)

        self.setLayout(layout)

    def selected_class_id(self):
        return self.button_group.checkedId()

def get_class_name(class_id):
    class_dict = {
        0: "green",
        1: "red",
        2: "yellow",
        3: "black",
        4: "green_blink",
        5: "red_blink",
        6: "yellow_blink",
        7: "unknown",
    }
    if class_id<len(class_dict):
        return class_dict[class_id]
    else:
        raise ValueError("over-class id: {}".format(class_id))

def get_class_id(class_name):
    class_dict = {
        "green": 0,
        "red": 1,
        "yellow": 2,
        "black": 3,
        "green_blink": 4,
        "red_blink": 5,
        "yellow_blink": 6,
        "unknown": 7,
        "black_blink": 4 # Temporal
    }
    if class_name in class_dict:
        return class_dict[class_name]
    else:
        raise ValueError("Unknown class name: {}".format(class_name))
    
def get_class_color(class_id):
    no_blink, blink = 255, 255
    class_dict = {
        0: (0, 255, 0    , no_blink),
        1: (255, 0, 0    , no_blink),
        2: (255, 255, 0  , no_blink),
        3: (255, 255, 255, no_blink),
        4: (0, 255, 0    , blink),
        5: (255, 0, 0    , blink),
        6: (255, 255, 0  , blink),
        7: (128, 128, 128, blink)
    }
    if class_id<len(class_dict):
        return class_dict[class_id]
    else:
        raise ValueError("over-class id: {}".format(class_id))

def get_color_by_id(label_id):
    # 使用HSV颜色空间，更容易区分颜色
    hue = int((120 + 45 * (label_id % 8)) % 360)
    saturation = 255
    value = 255
    return QColor.fromHsv(hue, saturation, value)

class CustomQLabel(QLabel):
    def __init__(self, image_viewer, parent=None):
        super().__init__(parent)
        self.image_viewer = image_viewer

    def mouseMoveEvent(self, event):
        pos = event.pos()
        x, y = pos.x(), pos.y()
        
        x_ratio, y_ratio = self.image_viewer.get_scale_ratio()
        original_x = int(x / x_ratio)
        original_y = int(y / y_ratio)
        
        self.image_viewer.coord_label.setText("x: {}, y: {}".format(original_x, original_y))

class ImageViewer(QWidget):
    def __init__(self, clip_dir):
        super().__init__()
        self.clip_dir = clip_dir
        self.clip = CLIP(clip_dir)

        # 获取图片文件列表
        self.image_paths = self.clip.get_all_image_paths()
        self.show_bbox_color = True
        self.show_bbox_blink_state = False

        # 初始化界面
        self.init_ui()

        # 初始化定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_image)
        self.timer.start(50)  # 定时默认间隔50ms，20Hz

    def init_ui(self):
        # 设置窗口标题和大小
        self.setWindowTitle("Image Viewer")
        self.setGeometry(100, 100, 800, 600)

        # 在image_label之前添加一个新的标签用于显示坐标
        self.coord_label = QLabel(self)
        self.coord_label.setAlignment(Qt.AlignLeft)

        # 创建显示图片的标签
        #self.image_label = QLabel(self)
        self.image_label = CustomQLabel(self, self)
        # self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        # self.image_label.setMinimumSize(400, 400)
        self.image_label.setMaximumSize(1920, 1080)
        # self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.mousePressEvent = self.image_label_clicked
        self.image_label.setMouseTracking(True)

        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)  # 设置为可调整大小

        # 创建滑块
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(len(self.image_paths) - 1)

        # 创建控制按钮
        self.play_button = QPushButton('Play', self)

        # 创建水平布局，并添加滑块和控制按钮
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.slider)
        control_layout.addWidget(self.play_button)

        self.show_bbox = QCheckBox('Show BBox', self)
        control_layout.addWidget(self.show_bbox)
        self.show_bbox.stateChanged.connect(self.print_screen)
        
        self.show_track = QCheckBox('Show Track', self)
        control_layout.addWidget(self.show_track)
        self.show_track.stateChanged.connect(self.print_screen)

        # 创建垂直布局，并添加图片标签和控制布局
        layout = QVBoxLayout()
        layout.addWidget(self.scroll_area)
        # layout.addWidget(self.image_label)
        layout.addWidget(self.coord_label)
        layout.addLayout(control_layout)

        # 创建一个包含图片路径的列表窗口
        self.image_list = QListWidget()

        # 添加图片到 image_list
        for img_path in self.image_paths:
            item = QListWidgetItem(img_path)
            self.image_list.addItem(item)

        # 在图片列表下方添加跟踪信息显示区域
        self.tracking_info_area = QTreeWidget()
        self.tracking_info_area.setHeaderHidden(True)

        # 将图片列表和跟踪信息显示区域放入一个垂直布局
        left_side_layout = QVBoxLayout()
        left_side_layout.addWidget(self.image_list)
        left_side_layout.addWidget(self.tracking_info_area)

        # 使用QSplitter将图片列表和跟踪信息显示区域的布局与现有布局分开
        splitter = QSplitter(Qt.Horizontal)
        left_side_widget = QWidget()
        left_side_widget.setLayout(left_side_layout)
        splitter.addWidget(left_side_widget)

        main_widget = QWidget()
        main_widget.setLayout(layout)
        splitter.addWidget(main_widget)

        # 设置初始窗口部件宽度
        splitter.setSizes([100, 700])

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(splitter)

        # 为控件添加事件处理函数
        self.slider.valueChanged.connect(self.set_current_index)
        self.play_button.clicked.connect(self.toggle_play)
        self.image_list.currentRowChanged.connect(self.set_current_index)
        self.tracking_info_area.itemClicked.connect(self.on_tracking_info_item_clicked)

        # 设置初始状态
        self.current_index = 0
        self.highlighted_track_id = None
        self.playing = False
        self.update_tracking_info()  # 在初始化UI时调用更新跟踪信息的方法
        self.print_screen()
        
    def image_label_clicked(self, event):
        x, y = event.pos().x(), event.pos().y()
        self.select_bbox(x, y)

    def get_scale_ratio(self):
        pixmap_size = self.image_label.pixmap().size()
        label_size = self.image_label.size()
        x_ratio, y_ratio = label_size.width() / pixmap_size.width(), label_size.height() / pixmap_size.height()
        return (x_ratio, y_ratio)

    def select_bbox(self, x, y):
        x_ratio, y_ratio = self.get_scale_ratio()
        original_x = int(x / x_ratio)
        original_y = int(y / y_ratio)

        label_path = os.path.join(self.labels_dir, self.labels[self.current_index])
        with open(label_path, 'r') as f:
            lines = f.readlines()

        selected_bbox = None
        for index, line in enumerate(lines):
            label = line.strip().split(' ')
            x1, y1, x2, y2 = map(float, label[1:-1])
            selected_class_id  = get_class_id(label[-1])
            if x1 <= original_x <= x2 and y1 <= original_y <= y2:
                selected_bbox = index
                break

        if selected_bbox is not None:
            class_ids = {
                0: "green",
                1: "red",
                2: "yellow",
                3: "black",
                4: "green_blink",
                5: "red_blink",
                6: "yellow_blink",
                7: "unknown"
            }
            # 创建一个列表存储类ID和对应的颜色名称
            options = [f"{class_id}: {class_name}" for class_id, class_name in class_ids.items()]
            # 显示包含所有选项的对话框
            # selected_item, ok = QInputDialog.getItem(self, "Select Class ID", "Class:", options, selected_class_id, False)
            # new_class_id = int(selected_item.split(':')[0])
            # if ok:
            #     self.update_bbox_class_id(label_path, selected_bbox, new_class_id)
            #     self.print_screen()
            dialog = RadioButtonDialog(class_ids, selected_class_id, self)
            result = dialog.exec_()
            if result == QDialog.Accepted:
                new_class_id = dialog.selected_class_id()
                self.update_bbox_class_id(label_path, selected_bbox, new_class_id)
                self.print_screen()

    def update_bbox_class_id(self, label_path, bbox_index, new_class_id):
        with open(label_path, 'r') as f:
            lines = f.readlines()

        new_class_name = get_class_name(new_class_id) # 根据class_id找到对应的class_name
        bbox_info = lines[bbox_index].strip().split(' ')
        bbox_info[-1] = new_class_name
        new_line = ' '.join(bbox_info) + '\n'
        lines[bbox_index] = new_line

        with open(label_path, 'w') as f:
            f.writelines(lines)

    def set_current_index(self, value):
        self.current_index = value
        self.image_list.setCurrentRow(self.current_index)  # 高亮当前图片地址条目
        self.slider.setValue(self.current_index) # 滑块跟随移动
        self.print_screen()

    def toggle_play(self):
        self.playing = not self.playing
        if self.playing:
            self.play_button.setText('Pause')
            self.timer.start(10)
        else:
            self.play_button.setText('Play')
            self.timer.stop()

    def update_image(self):
        if self.playing:
            self.current_index += 1
            if self.current_index >= len(self.image_paths):
                self.current_index = 0
                self.playing = False
            self.print_screen()
            self.slider.setValue(self.current_index)
        else:
            self.play_button.setText('Play')

    def print_image(self):
        image_path = self.image_paths[self.current_index]
        image = QPixmap(image_path)
        self.image_label.setPixmap(image)
        # scaled_image = image.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # self.image_label.setPixmap(scaled_image)
    
    def print_screen(self):
        self.print_image()
        
        # 绘制 bounding box
        if self.show_bbox.isChecked():
            painter = QPainter(self.image_label.pixmap())
            
            # 读取对应帧的标签文件
            bboxes = self.clip.get_label_by_index(self.current_index)
            for bbox in bboxes:
                # 绘制 bounding box
                x1, y1, x2, y2 = bbox.ltrb
                color_name = bbox.color_name
                
                pen_size = max(1, min(x2 - x1, y2 - y1) // 5)  # 设置画笔的粗细，最小为1，最大为bounding box宽高中的较小值的1/50
                if self.show_bbox_color:
                    color = CLIP.color_name2color(color_name)
                else:
                    color = (255, 0, 0, 255)
                pen = QPen(QColor(*color), pen_size)  # 设置画笔颜色和粗细
                painter.setPen(pen)
                painter.drawRect(x1, y1, x2 - x1, y2 - y1)
                
                if self.show_bbox_blink_state:
                    if bbox.blink_state:
                        # 绘制blink圆形
                        radius = (x2 - x1) // 2.5
                        painter.setPen(QPen(Qt.NoPen))
                        painter.setBrush(QBrush(QColor(255, 165, 0, 255)))
                        if y1 - radius*2 > radius:
                            painter.drawEllipse((x1 + x2) // 2 - radius, y1 - radius*3, radius * 2, radius * 2)
                        else:
                            painter.drawEllipse((x1 + x2) // 2 - radius, y2 + radius*3, radius * 2, radius * 2)
            painter.end()
            
        if self.show_track.isChecked():
            painter = QPainter(self.image_label.pixmap())
            # 读取对应帧的标签文件
            bboxes = self.clip.get_label_by_index(self.current_index)
            for bbox in bboxes:
                # 绘制 bounding box
                x1, y1, x2, y2 = bbox.ltrb
                track_id = bbox.track_id
                if track_id==None or track_id==-1:
                    continue
                color = get_color_by_id(track_id)

                # 适当扩大bounding box绘画的范围，这里扩大了10%的宽和高
                x1 -= (x2 - x1) * 0.1
                y1 -= (y2 - y1) * 0.1
                x2 += (x2 - x1) * 0.1
                y2 += (y2 - y1) * 0.1

                pen_size = max(1, min(x2 - x1, y2 - y1) // 10)  # 设置画笔的粗细，最小为1，最大为bounding box宽高中的较小值的1/50
                pen = QPen(color, pen_size)  # 设置画笔颜色和粗细
                painter.setPen(pen)
                painter.drawRect(x1, y1, x2 - x1, y2 - y1)
                
                # 绘制带底色的ID文本
                font_size = max(pen_size * 2, 10)  # 设定字体大小的最小值为10
                font = painter.font()
                font.setPointSize(font_size)
                painter.setFont(font)
                painter.setPen(QPen(Qt.NoPen))
                painter.setBrush(QBrush(color))
                text_rect = QRectF(x1, y2, font_size * len(str(track_id)), font_size * 1.5)
                painter.fillRect(text_rect, color)
                painter.setPen(QPen(Qt.black, 1))
                painter.drawText(text_rect, Qt.AlignCenter, str(track_id))
                
                if self.highlighted_track_id == track_id:
                    painter.setPen(QPen(Qt.white, 2))  # 设置白色边框，线宽为2
                    painter.setBrush(QBrush(Qt.NoBrush))
                    painter.drawRect(text_rect)
                
                painter.setPen(QPen(Qt.NoPen))
                painter.setBrush(QBrush(Qt.NoBrush))

            painter.end()

    def update_tracking_info(self):
        # 清空跟踪信息显示区域
        self.tracking_info_area.clear()

        # 遍历跟踪信息并添加到跟踪信息显示区域
        for track_info in self.clip.tracking_info:
            # 创建ID条目
            track_item = QTreeWidgetItem(self.tracking_info_area, [f"ID: {track_info['id']}"])
            track_item.setData(0, Qt.UserRole, track_info['start_frame']-1)

            # 添加子条目
            start_frame_item = QTreeWidgetItem(track_item, [f"Start Frame: {track_info['start_frame']}"])
            start_frame_item.setData(0, Qt.UserRole, track_info['start_frame']-1)
            end_frame_item = QTreeWidgetItem(track_item, [f"End Frame: {track_info['end_frame']}"])
            end_frame_item.setData(0, Qt.UserRole, track_info['end_frame']-1)
            
            frame_count_item = QTreeWidgetItem(track_item)
            frame_count_item.setText(0, f"Frame Count: {track_info['frame_count']}")
            avg_conf_item = QTreeWidgetItem(track_item)
            avg_conf_item.setText(0, f"Average Confidence: {track_info['average_confidence']}")

        # 将QTreeWidget展开到一个层级
        # self.tracking_info_area.expandToDepth(0)

    def on_tracking_info_item_clicked(self, item, column):
        parent_item = item.parent()
        if parent_item is not None:
            track_id = int(parent_item.text(0).split(":")[-1].strip())
        else:
            track_id = int(item.text(0).split(":")[-1].strip())
        self.highlighted_track_id = track_id
        
        frame_index = item.data(column, Qt.UserRole)
        if frame_index is not None:
            self.set_current_index(frame_index)



if __name__ == '__main__':
    app = QApplication([])    
    root_dir = r"C:\Users\qj00241.7HORSE\Downloads\test_data\TlightClipData"
    clips_imgs_dir = os.path.join(root_dir, "tl_imgs")
    
    clip_name = "clp_1675339721350"
    clip_img_dir = os.path.join(clips_imgs_dir, clip_name)
    
    
    viewer = ImageViewer(clip_img_dir) # labels_dir
    viewer.show()
    app.exec_()
