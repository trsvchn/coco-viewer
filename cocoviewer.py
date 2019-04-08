import argparse
import os
import json
import tkinter as tk
import logging

from PIL import Image, ImageDraw, ImageTk


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

parser = argparse.ArgumentParser(description='View images with bboxes from COCO dataset')
parser.add_argument('-i', '--images', default='', type=str, metavar='PATH', help='path to image folder')
parser.add_argument('-a', '--annotations', default='', type=str, metavar='PATH', help='path to annotations json file')


class App(tk.Tk):
    """Main App class.
    # TODO: Implement predicted bboxes drawing (from custom models).
    """
    def __init__(self,
                 path_to_images: str,
                 path_to_gt_anns: str,
                 path_to_pred_anns: str = None) -> None:
        super().__init__()

        self.path_to_images = path_to_images
        self.path_to_gt_anns = path_to_gt_anns
        self.path_to_pred_anns = path_to_pred_anns
        self.image = None
        self.instances = None
        self.images = None

        self.print_debug()

        self.load_annotations()
        self.get_images()

        self.current_image = self.images.next()  # set the first image as current
        self.load_image(self.current_image, start=True)  # load first image

        self.bind("<Left>", self.previous_image)
        self.bind("<Right>", self.next_image)
        # TODO: ADD exit button.

    def load_annotations(self) -> None:
        """Loads annotations file.
        """
        if '.json' in self.path_to_gt_anns:
            logging.info('Parsing json...')

        with open(self.path_to_gt_anns) as f:
            instances = json.load(f)

        self.instances = instances

    def get_images(self) -> None:
        """Extracts all image ids and file names from annotations file.
        """
        self.images = ImageList([(image['id'], image['file_name']) for image in self.instances['images']])

    def get_objects(self, image_id: int) -> list:
        """Extracts all object from annotations file for image with image_id.
        """
        return [obj for obj in self.instances['annotations'] if obj['image_id'] == image_id]

    def load_image(self, image: tuple, start=False):
        """Loads image and represents it as label widget.
        """
        img_id, img_name = image

        full_path = os.path.join(self.path_to_images, img_name)

        # Open image
        img_open = Image.open(full_path).convert('RGBA')

        # Create layer for bbox
        bbox_layer = Image.new('RGBA', img_open.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(bbox_layer)

        # test bbox
        #draw.rectangle(xy=[300, 100, 500, 300], fill=(255, 0, 0, 80), outline=(255, 0, 0, 0))

        objects = self.get_objects(img_id)

        # Extract bbox coordinates
        bboxes = [[obj['bbox'][0],
                   obj['bbox'][1],
                   obj['bbox'][0] + obj['bbox'][2],
                   obj['bbox'][1] + obj['bbox'][3]] for obj in objects]

        # draw bboxes
        for b in bboxes:
            draw.rectangle(b, fill=(255, 0, 0, 80), outline=(255, 0, 0, 0))

        del draw

        composed_img = Image.alpha_composite(img_open, bbox_layer)

        if start:
            # loading the very first image
            img = ImageTk.PhotoImage(composed_img)
            self.image = tk.Label(self, image=img)
            # self.image.image = img
            self.image.pack()

        img = ImageTk.PhotoImage(composed_img)
        self.image.configure(image=img)
        self.image.image = img

    def print_debug(self):
        logging.info('Starting app...')

    def next_image(self, event):
        """Loads the next image in a list.
        """
        if event:
            self.load_image(self.images.next())

    def previous_image(self, event):
        """Loads the previous image in a list.
        """
        if event:
            self.load_image(self.images.prev())


class ImageList:
    """Handles iterating through the images.

       NOTE: image list are built based on annotations file, not image folder content!
    """
    def __init__(self, images):
        self.image_list = images
        self.n = -1
        self.max = len(images)
        self.min = -2

    def next(self):
        """Sets the next image as current.
        """
        self.n += 1

        if self.n < self.max:
            current_image = self.image_list[self.n]
        else:
            self.n = 0
            current_image = self.image_list[self.n]

        return current_image

    def prev(self):
        """Sets the previous image as current.
        """
        if self.n == 0:
            self.n = self.max - 1
            current_image = self.image_list[self.n]
        else:
            self.n -= 1
            current_image = self.image_list[self.n]

        return current_image


def main():
    """Runs app.
    """
    args = parser.parse_args()
    app = App(args.images, args.annotations)
    app.mainloop()


if __name__ == "__main__":
    main()
