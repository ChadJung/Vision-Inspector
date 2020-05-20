import tensorflow as tf
from keras.preprocessing.image import img_to_array
from KoreanPathCV2 import imread, imwrite
from object_detection.utils import label_map_util
import numpy as np
import imutils
import cv2

model_path = 'model/frozen_inference_graph.pb'
label_path = 'model/classes.pbtxt'
num_classes = 10
min_confidence = 0.3

class InspectionClass():
    def __init__(self):
        self.ins_labels = [0, 1, 2, 3] # Labels that are being inspected

        # initialize the model
        self.model = tf.Graph()

        with self.model.as_default():
        	# initialize the graph definition
        	graphDef = tf.GraphDef()

        	# load the graph from disk
        	with tf.gfile.GFile(model_path, "rb") as f:
        		serializedGraph = f.read()
        		graphDef.ParseFromString(serializedGraph)
        		tf.import_graph_def(graphDef, name="")

        # load the class labels from disk
        labelMap = label_map_util.load_labelmap(label_path)
        categories = label_map_util.convert_label_map_to_categories(
        	labelMap, max_num_classes=num_classes,
        	use_display_name=True)
        self.categoryIdx = label_map_util.create_category_index(categories)

        # create a session to perform inference
        with self.model.as_default():
        	self.sess = tf.Session(graph=self.model)

        # grab a reference to the input image tensor and the boxes
        # tensor
        self.imageTensor = self.model.get_tensor_by_name("image_tensor:0")
        self.boxesTensor = self.model.get_tensor_by_name("detection_boxes:0")

        # for each bounding box we would like to know the score
        # (i.e., probability) and class label
        self.scoresTensor = self.model.get_tensor_by_name("detection_scores:0")
        self.classesTensor = self.model.get_tensor_by_name("detection_classes:0")
        self.numDetections = self.model.get_tensor_by_name("num_detections:0")

        image = imread('test.jpg', cv2.IMREAD_COLOR)
        self.inspection(image)


    def inspection(self, image):
        result = False
        res_labels = [False] * num_classes

        # prepare the image for detection
        (H, W) = image.shape[:2]

        if W > H and W > 640:
        	image = imutils.resize(image, width=640)

        # # otherwise, check to see if we should resize along the
        # # height
        elif H > W and H > 480:
        	image = imutils.resize(image, height=480)

        (H, W) = image.shape[:2]

        output = image.copy()

        image = cv2.cvtColor(image.copy(), cv2.COLOR_BGR2RGB)
        image = np.expand_dims(image, axis=0)

        # perform inference and compute the bounding boxes,
        # probabilities, and class labels
        (boxes, scores, labels, N) = self.sess.run(
            [self.boxesTensor, self.scoresTensor, self.classesTensor, self.numDetections],
            feed_dict={self.imageTensor: image})

        # squeeze the lists into a single dimension
        boxes = np.squeeze(boxes)
        scores = np.squeeze(scores)
        labels = np.squeeze(labels)

        cv2.rectangle(output, (1, 1), (637, 532), (0, 255, 0), 3)

        # loop over the bounding box predictions
        for (box, score, label) in zip(boxes, scores, labels):
            # if the predicted probability is less than the minimum
            # confidence, ignore it
            if score < min_confidence:
                continue
            
            # scale the bounding box from the range [0, 1] to [W, H]
            (startY, startX, endY, endX) = box
            startX = int(startX * W)
            startY = int(startY * H)
            endX = int(endX * W)
            endY = int(endY * H)

            
            # draw the prediction on the output image
            label = self.categoryIdx[label]
            idx = int(label["id"]) - 1
            labels[idx] = True
            if idx not in self.ins_labels:
                continue

            showlabel = "{}: {} = {:.2f}".format(idx, label["name"], score)
                
            cv2.rectangle(output, (startX, startY), (endX, endY), (0, 0, 255), 2)
            cv2.putText(output, showlabel, (startX, startY), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 2)
            result = True
            
        if result:
            cv2.rectangle(output, (1, 1), (637, 532), (0, 0, 255), 5)
        # print('returning:', result)
        return [res_labels[i] for i in self.ins_labels], result, output
