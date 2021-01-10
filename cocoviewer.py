#!/usr/bin/env python3
"""COCO Dataset Viewer.

View images with bboxes from the COCO dataset.
"""
import argparse
import os
import random
import colorsys
import json
import logging
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageDraw, ImageTk

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

parser = argparse.ArgumentParser(description="View images with bboxes from the COCO dataset")
parser.add_argument("-i", "--images", default='', type=str, metavar="PATH", help="path to images folder")
parser.add_argument("-a", "--annotations", default='', type=str, metavar="PATH", help="path to annotations json file")


class ImageWidget:
    """Main Image Widget that displays composed image.
    """
    # TODO: labels for object classes
    # TODO: predicted bboxes drawing (from models)
    def __init__(self, parent, image_dir=None, annotations_file=None) -> None:
        self.parent = parent
        self.image = tk.Label(self.parent)

        if image_dir and annotations_file:
            self.image_dir = image_dir
            instances, images, categories = parse_coco(annotations_file)
            self.instances = instances
            self.images = ImageList(images)  # NOTE: image list is based on annotations file
            self.categories = categories
            self.current_image = self.images.next()  # Set the first image as current
            self.composed_img = None  # To store composed PIL Image
            # Load the very first image
            self.load_image(self.current_image)
            img = ImageTk.PhotoImage(self.composed_img)
            # Init the image widget
            self.image.config(image=img)
            self.image.pack()
            self.image.image = img
        else:
            self.image.pack()

    def exit(self, event):
        if event:
            self.parent.destroy()

    def load_image(self, image: tuple):
        """Loads image as PIL Image.
        """
        # TODO: function is too long
        img_id, img_name = image
        full_path = os.path.join(self.image_dir, img_name)
        # Open image
        img_open = Image.open(full_path).convert("RGBA")
        # Create layer for bbox
        bbox_layer = Image.new("RGBA", img_open.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(bbox_layer)

        # test bbox
        # draw.rectangle(xy=[300, 100, 500, 300], fill=(255, 0, 0, 80), outline=(255, 0, 0, 0))

        # Get objects
        objects = [obj for obj in self.instances["annotations"] if obj["image_id"] == img_id]
        obj_categories = [self.categories[obj["category_id"]] for obj in objects]

        # Extracting bbox coordinates
        bboxes = [[obj["bbox"][0],
                   obj["bbox"][1],
                   obj["bbox"][0] + obj["bbox"][2],
                   obj["bbox"][1] + obj["bbox"][3]] for obj in objects]

        # Extracting masks
        masks = True
        if masks:
            masks = [obj["segmentation"] for obj in objects]

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

        self.composed_img = Image.alpha_composite(img_open, bbox_layer)

    def save_image(self, event=None):
        """Saves composed image as png file.
        """
        # Initial (original) file name
        initialfile = self.current_image[-1].split(".")[0]
        # TODO: Add more formats, at least jpg (RGBA -> RGB)?
        filetypes = (("png files", "*.png"), ("all files", "*.*"))
        # By default save as png file
        defaultextension = ".png"

        file = filedialog.asksaveasfilename(
            initialfile=initialfile,
            filetypes=filetypes,
            defaultextension=defaultextension,
        )
        # If not canceled:
        if file:
            self.composed_img.save(file)

    def update_image(self):
        """Updates Image Label Widget.
        """
        img = ImageTk.PhotoImage(self.composed_img)
        # Update the image widget
        self.image.configure(image=img)
        self.image.image = img

    def next_image(self, event):
        """Loads the next image in a list.
        """
        if event:
            self.current_image = self.images.next()
            self.load_image(self.current_image)
            self.update_image()

    def previous_image(self, event):
        """Loads the previous image in a list.
        """
        if event:
            self.current_image = self.images.prev()
            self.load_image(self.current_image)
            self.update_image()


def parse_coco(annotations_file: str) -> tuple:
    """Parses COCO json annotation file.
    """
    instances = load_annotations(annotations_file)
    images = get_images(instances)
    categories = get_categories(instances)
    return instances, images, categories


def load_annotations(fname: str) -> dict:
    """Loads annotations file.
    """
    logging.info(f"Parsing {fname}...")

    with open(fname) as f:
        instances = json.load(f)
    return instances


def get_images(instances: dict) -> list:
    """Extracts all image ids and file names from annotations file.
    """
    return [(image["id"], image["file_name"]) for image in instances["images"]]


def get_categories(instances: dict) -> dict:
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
    categories = list(zip([[category["id"], category["name"]] for category in instances["categories"]], colors))
    categories = dict([[cat[0][0], [cat[0][1], cat[1]]] for cat in categories])
    return categories


def menu(root, image):
    """Adds a Menu bar.
    """
    menu_bar = tk.Menu(root)
    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="Save", accelerator="Ctrl+S", command=image.save_image)

    file_menu.add_separator()
    file_menu.add_command(label="Exit", accelerator="Ctrl+Q", command=root.destroy)
    menu_bar.add_cascade(label="File", menu=file_menu)
    root.config(menu=menu_bar)


def bind_events(root, image):
    """Binds events.
    """
    root.bind("<Left>", image.previous_image)
    root.bind("<k>", image.previous_image)
    root.bind("<Right>", image.next_image)
    root.bind("<j>", image.next_image)
    root.bind("<Control-q>", image.exit)
    root.bind("<Control-w>", image.exit)
    root.bind("<Control-s>", image.save_image)


class ImageList:
    """Handles iterating through the images.
    """
    def __init__(self, images: list):
        self.image_list = images or []
        self.n = -1
        self.max = len(self.image_list)

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


def print_info(message: str):
    logging.info(message)


def main():
    print_info("Starting the app...")
    args = parser.parse_args()
    root = tk.Tk()
    root.title("COCO Viewer")

    if not args.images or not args.annotations:
        root.geometry("300x150")  # app size when no data is provided
        messagebox.showwarning("Warning!", "Nothing to show.\nPlease specify path to coco dataset!")

    image = ImageWidget(root, args.images, args.annotations)
    menu(root, image)
    bind_events(root, image)
    root.mainloop()


if __name__ == "__main__":
    main()
