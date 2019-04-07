import os
import json
import tkinter as tk
import logging

from PIL import Image, ImageDraw, ImageTk


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


TEST_IMAGES = 'val2017'
TEST_ANNOTATIONS = 'annotations/instances_val2017.json'


class App(tk.Tk):
    """Main App class"""

    def __init__(self, path_to_images: str,
                 path_to_gt_anns: str,
                 path_to_pred_anns: str = None) -> None:
        super().__init__()

        self.path_to_images = path_to_images
        self.path_to_gt_anns = path_to_gt_anns
        self.path_to_pred_anns = path_to_pred_anns
        self.image = None
        self.print_debug()
        self.image_list = self.anns_parser()
        self.current_image = self.image_list.next()
        self.load_image(self.current_image, start=True)
        self.bind("<Left>", self.previous_image)
        self.bind("<Right>", self.next_image)

    def anns_parser(self):
        """Parse annotations file"""

        if '.json' in self.path_to_gt_anns:
            logging.info('Parsing json...')
        with open(self.path_to_gt_anns) as f:
            instances = json.load(f)
        return iter(ImageList([(image['id'], image['file_name']) for image in instances['images']]))

    def load_image(self, image_name: tuple, start=False):
        """Load image and represent it as label widget"""

        full_path = os.path.join(self.path_to_images, image_name[1])

        # Open image
        img_open = Image.open(full_path).convert('RGBA')

        # Create layer for bbox
        bbox_layer = Image.new('RGBA', img_open.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(bbox_layer)

        # test bbox
        draw.rectangle(xy=[300, 100, 500, 300], fill=(255, 0, 0, 80), outline=(255, 0, 0, 0))

        composed_img = Image.alpha_composite(img_open, bbox_layer)

        if start:
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
        if event:
            self.load_image(self.image_list.next())

    def previous_image(self, event):
        if event:
            self.load_image(self.image_list.prev())


class ImageList:
    """Handles iterating through the images."""

    def __init__(self, image_list):
        self.image_list = image_list
        self.max = len(image_list)

    def __iter__(self):
        self.n = 0
        return self

    def __next__(self):
        self.next()

    def next(self):
        if self.n < self.max:
            current_image = self.image_list[self.n]
            self.n += 1
        else:
            self.n = 0
            current_image = self.image_list[self.n]
            self.n += 1
        return current_image

    def prev(self):
        if self.n > -1:
            current_image = self.image_list[self.n]
            self.n -= 1
        else:
            self.n = self.max - 1
            current_image = self.image_list[self.n]
            self.n -= 1
        return current_image


if __name__ == "__main__":
    app = App(TEST_IMAGES, TEST_ANNOTATIONS)
    app.mainloop()
