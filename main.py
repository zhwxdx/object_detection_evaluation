import os
import sys

import numpy as np

import onnx
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QMessageBox
from PyQt5 import QtCore, QtGui
from src.ui.main_ui import Ui_Dialog as Main_UI
from src.ui import db_ui, visual_ui, visual_backend
from src.datasets.draw import draw_all
import matplotlib
matplotlib.use("Qt5Agg")
from src.database.db import DBManager

class Stream(QtCore.QObject):
    """Redirects console output to text widget."""
    newText = QtCore.pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))

class Main_Dialog(QMainWindow, Main_UI):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.current_directory = os.path.dirname(os.path.realpath(__file__))
        # Define error msg dialog
        self.msgBox = QMessageBox()

        # Default values
        self.dir_model_gt = None
        self.dir_images_gt = None
        self.filepath_classes_gt = None
        self.dir_dets = None
        self.filepath_classes_det = None
        self.dir_save_results = None
        self.ret = ''
        self.process_method=''
        self.result_csv=None

        self.center_screen()
        sys.stdout = Stream(newText=self.onUpdateText)


    def onUpdateText(self, text):
        """Write console output to text widget."""
        cursor = self.process.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.process.setTextCursor(cursor)
        self.process.ensureCursorVisible()

    def center_screen(self):
        size = self.size()
        desktopSize = QtWidgets.QDesktopWidget().screenGeometry()
        top = (desktopSize.height() / 2) - (size.height() / 2)
        left = (desktopSize.width() / 2) - (size.width() / 2)
        self.move(left, top)

    def closeEvent(self, event):
        conf = self.show_popup('Are you sure you want to close the program?',
                               'Closing',
                               buttons=QMessageBox.Yes | QMessageBox.No,
                               icon=QMessageBox.Question)
        if conf == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def show_popup(self,
                   message,
                   title,
                   buttons=QMessageBox.Ok | QMessageBox.Cancel,
                   icon=QMessageBox.Information):
        self.msgBox.setIcon(icon)
        self.msgBox.setText(message)
        self.msgBox.setWindowTitle(title)
        self.msgBox.setStandardButtons(buttons)
        return self.msgBox.exec()

    def comboSelectionChanged(self,index):
        text = self.combobox_process.itemText(index)
        if text=='yolov3':
            self.process_method='yolov3'
        elif text=='yolov5':
            self.process_method='yolov5'

    def load_annotations_gt(self):

        if self.rad_gt_format_coco_json.isChecked():
            self.ret='coco'
        elif self.rad_gt_format_pascalvoc_xml.isChecked():
            self.ret='voc'
        elif self.rad_gt_format_yolo_text.isChecked():
            self.ret='darknet'
        if self.ret=='':
            print("no format select")
            exit(-1)

    def btn_gt_statistics_clicked(self):
        pass

    def btn_gt_dir_clicked(self):
        if self.txb_gt_dir.text() == '':
            txt = self.current_directory
        else:
            txt = self.txb_gt_dir.text()
        directory = QFileDialog.getOpenFileName(
            self, 'Choose file with onnx model', txt)
        if directory == '':
            return
        file_path=directory[0]
        if os.path.isfile(file_path):
            self.txb_gt_dir.setText(file_path)
            self.dir_model_gt = file_path
        else:
            self.dir_model_gt = None
            self.txb_gt_dir.setText('')

    def btn_gt_classes_clicked(self):
        filepath = QFileDialog.getOpenFileName(self, 'Choose a file with a list of classes',
                                               self.current_directory,
                                               "Image files (*.txt *.names)")
        filepath = filepath[0]
        if os.path.isfile(filepath):
            self.txb_classes_gt.setText(filepath)
            self.filepath_classes_gt = filepath
        else:
            self.filepath_classes_gt = None

    def btn_gt_images_dir_clicked(self):
        if self.txb_gt_images_dir.text() == '':
            txt = self.current_directory
        else:
            txt = self.txb_gt_images_dir.text()
        directory = QFileDialog.getExistingDirectory(self,
                                                     'Choose directory with ground truth images',
                                                     txt)
        if directory != '':
            self.txb_gt_images_dir.setText(directory)
            self.dir_images_gt = directory

    def btn_det_classes_clicked(self):
        filepath = QFileDialog.getOpenFileName(self, 'Choose a file with a list of classes',
                                               self.current_directory,
                                               "Image files (*.txt *.names)")
        filepath = filepath[0]
        if os.path.isfile(filepath):
            self.txb_classes_det.setText(filepath)
            self.filepath_classes_det = filepath
        else:
            self.filepath_classes_det = None
            self.txb_classes_det.setText('')

    def btn_det_dir_clicked(self):
        if self.txb_det_dir.text() == '':
            txt = self.current_directory
        else:
            txt = self.txb_det_dir.text()
        directory = QFileDialog.getExistingDirectory(self, 'Choose directory with detections', txt)
        if directory == '':
            return
        if os.path.isdir(directory):
            self.txb_det_dir.setText(directory)
            self.dir_dets = directory
        else:
            self.dir_dets = None

    def btn_output_dir_clicked(self):
        if self.txb_output_dir.text() == '':
            txt = self.current_directory
        else:
            txt = self.txb_output_dir.text()
        directory = QFileDialog.getExistingDirectory(self, 'Choose directory to save the results',
                                                     txt)
        if os.path.isdir(directory):
            self.txb_output_dir.setText(directory)
            self.dir_save_results = directory
        else:
            self.dir_save_results = None

    # def btn_draw_clicked(self):
    #    self.process.setVisible(False)
    #    self.groupBox.setVisible(True)
    #    plt= DBManager().draw()
    #    self.gridlayout.addWidget(plt, 0, 2)

    def btn_save_clicked(self):
        if self.result_csv is None:
            print("error")
        else:
            DB=DBManager()
            result_csv = self.result_csv.split("\n")
            #each class
            class_name=result_csv[4].split(",")
            model_name = os.path.splitext(os.path.split(self.dir_model_gt)[1])[0]
            dataset_name = os.path.splitext(os.path.split(self.dir_images_gt)[1])[0]
            AP_class,F1_class,prec_class,rec_class,threshold_class,TP_class,FP_class,FN_class=result_csv[6].split(","),result_csv[7].split(","),\
                                                                   result_csv[8].split(","),result_csv[9].split(","),result_csv[10].split(",")\
                ,result_csv[11].split(","),result_csv[12].split(","),result_csv[13].split(",")

            TP_all,FP_all,FN_all=0,0,0

            #id, model_name, dataset, class, [f1, fp, tp, fn, map, prec, recall], threshold(best select by f1)
            for i,name_cl in enumerate(class_name):
                if name_cl=='class_names 'or name_cl=='':
                    continue
                else:
                    map_cl=0
                    ap_cl,tp_cl,fp_cl,fn_cl,F1_cl,prec_cl,rec_cl,thre_cl=AP_class[i],TP_class[i],FP_class[i],\
                                                                         FN_class[i],F1_class[i],prec_class[i],rec_class[i],threshold_class[i]
                    TP_all+=int(tp_cl)
                    FP_all+=int(fp_cl)
                    FN_all+=int(fn_cl)

                DB.add_item(model_name, dataset_name,name_cl,tp_cl,fp_cl,fn_cl,F1_cl,ap_cl,map_cl,prec_cl,rec_cl,thre_cl)

            #save all classes metric
            result_metric = result_csv[2].split(",")
            map,recall,F1_,Precision = float(result_metric[0]),float(result_metric[1]),float(result_metric[2]),float(result_metric[3])

            DB.add_item(model_name,dataset_name, "all",TP_all,FP_all,FN_all,F1_,0,map, Precision,recall,thre_cl)
    def btn_db(self):
        self.Dialog.hide()

        dialog1 = QtWidgets.QDialog()
        personalPage = db_ui.Ui_Dialog()
        personalPage.setupUi(dialog1)
        # personalPage.center()
        dialog1.show()
        dialog1.exec_()
        # dialog1.show()
        # dialog1.exec_()
        self.Dialog.show()
    def btn_visual(self):
        # self.Dialog.hide()

        a = visual_backend.Main_Dialog()
        # personalPage.center()
        a.Dialog.show()
        # a.Dialog.exec_()
        # dialog1.show()
        # dialog1.exec_()
        # self.Dialog.show()
    def btn_run_clicked(self):
        if self.rad_gt_format_coco_json.isChecked():
            self.ret = 'coco'
        elif self.rad_gt_format_pascalvoc_xml.isChecked() or self.rad_gt_format_labelme_xml.isChecked():
            self.ret = 'voc'
        elif self.rad_gt_format_yolo_text.isChecked():
            self.ret = 'darknet'
        if self.ret == '':
            print("no format select")
            exit(-1)
        evaluation = onnx.ONNX(self.dir_model_gt, 64, self.dir_images_gt, self.filepath_classes_gt, self.ret,
                               self.process_method)
        self.result_csv = evaluation.evaluate()

if __name__=='__main__':
    app = QtWidgets.QApplication(sys.argv)

    ui = Main_Dialog()
    ui.show()

    sys.exit(app.exec_())