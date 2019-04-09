"""Main app module.
"""
import os
import random
import colorsys
import json
import logging
import tkinter as tk

from PIL import Image, ImageDraw, ImageTk

from navigation import ImageList

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


class App(tk.Tk):
    """Main App class.
    """
    # TODO: labels for classes
    # TODO: predicted bboxes drawing (from custom models).
    # TODO: ADD exit button.
    def __init__(self,
                 path_to_images: str,
                 path_to_gt_anns: str,
                 path_to_pred_anns: str = None) -> None:
        super().__init__()

        self.path_to_images = path_to_images
        self.path_to_gt_anns = path_to_gt_anns
        self.path_to_pred_anns = path_to_pred_anns
        self.image = None

        self.instances = self.load_annotations()
        self.images = ImageList(self.get_images())  # NOTE: image list is based on annotations file
        self.categories = self.get_categories()

        self.print_debug()

        self.current_image = self.images.next()  # set the first image as current
        self.load_image(self.current_image, start=True)  # load first image

        self.bind("<Left>", self.previous_image)
        self.bind("<Right>", self.next_image)

    def load_annotations(self) -> dict:
        """Loads annotations file.
        """
        if '.json' in self.path_to_gt_anns:
            logging.info('Parsing json...')

        with open(self.path_to_gt_anns) as f:
            instances = json.load(f)
        return instances

    def get_images(self) -> list:
        """Extracts all image ids and file names from annotations file.
        """
        return [(image['id'], image['file_name']) for image in self.instances['images']]

    def get_objects(self, image_id: int) -> list:
        """Extracts all object from annotations file for image with image_id.
        """
        return [obj for obj in self.instances['annotations'] if obj['image_id'] == image_id]

    def get_categories(self) -> dict:
        """Extracts categories from annotations file and prepares color for each one.
        """
        # Get some colors
        hsv_tuples = [(x / 80, 1., 1.) for x in range(80)]
        colors = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
        colors = list(map(lambda x: (int(x[0] * 255), int(x[1] * 255), int(x[2] * 255)), colors))
        random.seed(42)
        random.shuffle(colors)
        random.seed(None)

        # Parse categories
        categories = list(zip([[category['id'], category['name']] for category in self.instances['categories']], colors))
        return dict([[cat[0][0], [cat[0][1], cat[1]]] for cat in categories])

    def load_image(self, image: tuple, start=False):
        """Loads image and represents it as label widget.
        """
        # TODO: function is too long
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
        obj_categories = [self.categories[obj['category_id']] for obj in objects]

        # Extracting bbox coordinates
        bboxes = [[obj['bbox'][0],
                   obj['bbox'][1],
                   obj['bbox'][0] + obj['bbox'][2],
                   obj['bbox'][1] + obj['bbox'][3]] for obj in objects]

        # Extracting masks
        masks = True
        if masks:
            masks = [obj['segmentation'] for obj in objects]

            # draw masks
            for c, m in zip(obj_categories, masks):
                alpha = 75
                fill = tuple(list(c[-1]) + [alpha])
                # Polygonal masks work fine
                if isinstance(m, list):
                    draw.polygon(m[0], outline=fill, fill=fill)
                # TODO: Fix problem with RLE
                # elif isinstance(m, dict):
                #     draw.polygon(m['counts'][1:-2], outline=c[-1], fill=fill)
                else:
                    continue

        # Draw bboxes
        for c, b in zip(obj_categories, bboxes):
            draw.rectangle(b, outline=c[-1])

        del draw

        composed_img = Image.alpha_composite(img_open, bbox_layer)

        if start:
            # Loading the very first image
            img = ImageTk.PhotoImage(composed_img)
            self.image = tk.Label(self, image=img)
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
