import os
import logging
from typing import final
import cv2
import torch
import matplotlib.pyplot as plt


class YoloModel:
    def __init__(self):
        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5x', pretrained=True)
        self.model.eval()
        self.output_video_fps = 15

    def predict(self, img):
        try:
            with torch.no_grad():
                result = self.model(img)
            result.save('api/static/results/')
            final_result = {}
            data = []
            file_name = f'static/{result.files[0]}'

            for i in range(len(result.xywhn[0])):
                x, y, w, h, prob, cls = result.xywhn[0][i].numpy()
                preds = {}
                preds['x'] = str(x)
                preds['y'] = str(y)
                preds['w'] = str(w)
                preds['h'] = str(h)
                preds['prob'] = str(prob)
                preds['class'] = result.names[int(cls)]
                data.append(preds)

            return {'file_name': file_name, 'bbox': data, 'mimetype': 'image'}
        except Exception as ex:
            logging.error(str(ex))
            return None
    
    def predict_video(self, video_url):
        try:
            cap = None
            writer = None

            cap = cv2.VideoCapture(video_url)
            frame_cnt = 0
            final_result = {}
            out_filename = video_url.split('/')[-1]
            avi_filename = os.path.splitext(out_filename)[0] + '.mp4'
            out_filepath = os.path.join('api/static/results', avi_filename)
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            writer = cv2.VideoWriter(out_filepath, cv2.VideoWriter_fourcc(*'mp4v'), self.output_video_fps, (frame_width, frame_height))
            filename = f'static/{avi_filename}'
            with torch.no_grad():
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    if frame_cnt > 25:
                        break
                    frame_cnt += 1
                    result = self.model(frame)
                    result.render()
                    writer.write(result.imgs[0])
                    data = []

                    for i in range(len(result.xywhn[0])):
                        x, y, w, h, prob, cls = result.xywhn[0][i].numpy()
                        preds = {}
                        preds['x'] = str(x)
                        preds['y'] = str(y)
                        preds['w'] = str(w)
                        preds['h'] = str(h)
                        preds['prob'] = str(prob)
                        preds['class'] = result.names[int(cls)]
                        data.append(preds)
                    final_result[frame_cnt] = data

                return {'file_name': filename, 'bbox': final_result, 'mimetype': 'video'}
        except Exception as e:
            logging.error(str(e))
            return None
        finally:
            if writer is not None:
                writer.release()
            if cap is not None:
                cap.release()
