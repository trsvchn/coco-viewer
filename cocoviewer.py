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


class Data:
    """Handles data related stuff.
    """
    def __init__(self, image_dir, annotations_file):
        self.image_dir = image_dir
        self.annotations_file = annotations_file
        instances, images, categories = parse_coco(self.annotations_file)
        self.instances = instances
        self.images = ImageList(images)  # NOTE: image list is based on annotations file
        self.categories = categories
        self.nobjects = None
        self.ncategories = None
        # Load and prepare the very first image
        self.current_image = self.images.next()  # Set the first image as current
        self.current_composed_image = None  # To store composed PIL Image
        self.compose_current_image()

    def compose_image(self, image: tuple, bboxes_on: bool = True, masks_on: bool = True):
        """Loads image as PIL Image and draw bboxes and/or masks.
        """
        # TODO: labels for object classes
        # TODO: predicted bboxes drawing (from models)
        img_id, img_name = image
        full_path = os.path.join(self.image_dir, img_name)
        # Open image
        img_open = Image.open(full_path).convert("RGBA")
        # Create layer for bboxes and masks
        draw_layer = Image.new("RGBA", img_open.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(draw_layer)
        # Get objects
        objects = [obj for obj in self.instances["annotations"] if obj["image_id"] == img_id]
        obj_categories = [self.categories[obj["category_id"]] for obj in objects]

        self.nobjects = len(objects)
        self.ncategories = len(set([obj["category_id"] for obj in objects]))

        # Prepare masks
        if masks_on:
            draw_masks(draw, objects, obj_categories)

        # Draw bounding boxes
        if bboxes_on:
            draw_bboxes(draw, objects, obj_categories)

        del draw
        # Set composed resulting image
        self.current_composed_image = Image.alpha_composite(img_open, draw_layer)

    def compose_current_image(self, **kwargs):
        self.compose_image(self.current_image, **kwargs)

    def next_image(self, **kwargs):
        """Loads the next image in a list.
        """
        self.current_image = self.images.next()
        self.compose_current_image(**kwargs)

    def previous_image(self, **kwargs):
        """Loads the previous image in a list.
        """
        self.current_image = self.images.prev()
        self.compose_current_image(**kwargs)


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


def draw_bboxes(draw, objects, obj_categories):
    """Puts rectangles on the image.
    """
    # Extracting bbox coordinates
    bboxes = [[obj["bbox"][0],
               obj["bbox"][1],
               obj["bbox"][0] + obj["bbox"][2],
               obj["bbox"][1] + obj["bbox"][3]] for obj in objects]
    # Draw bboxes
    for c, b in zip(obj_categories, bboxes):
        draw.rectangle(b, outline=c[-1])


def draw_masks(draw, objects, obj_categories):
    """Draws a masks over image.
    """
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


class ImageWidget(tk.Frame):
    """Main Image Widget that displays composed image.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.pack()

        self.image = tk.Label(self)
        self.image.pack(side=tk.TOP)

        self.statusbar = tk.Frame(parent, bg="gray75")
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.file_count = tk.Label(self.statusbar, bd=5, bg="gray75")
        self.file_count.pack(side=tk.RIGHT)
        self.description = tk.Label(self.statusbar, bd=5, bg="gray75")
        self.description.pack(side=tk.RIGHT)
        self.file_name = tk.Label(self.statusbar, bd=5, bg="gray75")
        self.file_name.pack(side=tk.LEFT)
        self.nobjects = tk.Label(self.statusbar, bd=5, bg="gray75")
        self.nobjects.pack(side=tk.LEFT)
        self.ncategories = tk.Label(self.statusbar, bd=5, bg="gray75")
        self.ncategories.pack(side=tk.LEFT)


class Controller:
    def __init__(self, root, image, data):
        self.root = root
        self.image = image
        self.data = data

        self.file_count_status = tk.StringVar()
        self.file_name_status = tk.StringVar()
        self.description_status = tk.StringVar()
        self.nobjects_status = tk.StringVar()
        self.ncategories_status = tk.StringVar()
        self.image.file_count.configure(textvariable=self.file_count_status)
        self.image.file_name.configure(textvariable=self.file_name_status)
        self.image.description.configure(textvariable=self.description_status)
        self.image.nobjects.configure(textvariable=self.nobjects_status)
        self.image.ncategories.configure(textvariable=self.ncategories_status)

        self.bboxes_on = tk.BooleanVar()
        self.bboxes_on.set(True)
        self.masks_on = tk.BooleanVar()
        self.masks_on.set(True)
        self.update_img()

        self.bind_events()

    def update_img(self):
        self.data.compose_current_image(bboxes_on=self.bboxes_on.get(), masks_on=self.masks_on.get())
        img = self.data.current_composed_image
        img = ImageTk.PhotoImage(img)
        self.image.image.configure(image=img)
        self.image.image.image = img
        self.file_count_status.set(f"{str(self.data.images.n + 1)}/{self.data.images.max}")
        self.file_name_status.set(f"{self.data.current_image[-1]}")
        self.description_status.set(f"{self.data.instances.get('info', '').get('description', '')}")
        self.nobjects_status.set(f"objects: {self.data.nobjects}")
        self.ncategories_status.set(f"categories: {self.data.ncategories}")

    def exit(self, event=None):
        print_info("Exiting...")
        self.root.quit()

    def next_img(self, event=None):
        self.data.next_image()
        self.update_img()

    def prev_img(self, event=None):
        self.data.previous_image()
        self.update_img()

    def save_image(self, event=None):
        """Saves composed image as png file.
        """
        # Initial (original) file name
        initialfile = self.data.current_image[-1].split(".")[0]
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
            self.data.compose_current_image.save(file)

    def toggle_bboxes(self, event=None):
        self.bboxes_on.set(not self.bboxes_on.get())
        self.update_img()

    def toggle_masks(self, event=None):
        self.masks_on.set(not self.masks_on.get())
        self.update_img()

    def toggle_all(self, event=None):
        var_list = [self.bboxes_on, self.masks_on]
        if True in set([var.get() for var in var_list]):
            [var.set(False) for var in var_list]
        else:
            [var.set(True) for var in var_list]
        self.update_img()

    def bind_events(self):
        """Binds events.
        """
        self.root.bind("<Left>", self.prev_img)
        self.root.bind("<k>", self.prev_img)
        self.root.bind("<Right>", self.next_img)
        self.root.bind("<j>", self.next_img)
        self.root.bind("<Control-q>", self.exit)
        self.root.bind("<Control-w>", self.exit)
        self.root.bind("<Control-s>", self.save_image)
        self.root.bind("<b>", self.toggle_bboxes)
        self.root.bind("<Control-b>", self.toggle_bboxes)
        self.root.bind("<m>", self.toggle_masks)
        self.root.bind("<Control-m>", self.toggle_masks)
        self.root.bind("<space>", self.toggle_all)


class Menu(tk.Menu):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.file()
        self.view()

    def file(self):
        """File Menu.
        """
        file_menu = tk.Menu(self, tearoff=0)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.controller.save_image)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", accelerator="Ctrl+Q", command=self.controller.exit)
        self.add_cascade(label="File", menu=file_menu)

    def view(self):
        """View Menu.
        """
        view_menu = tk.Menu(self, tearoff=0)
        view_menu.add_checkbutton(
            label="BBoxes",
            onvalue=True,
            offvalue=False,
            variable=self.controller.bboxes_on,
            command=self.controller.update_img,
        )
        view_menu.add_checkbutton(
            label="Masks",
            onvalue=True,
            offvalue=False,
            variable=self.controller.masks_on,
            command=self.controller.update_img,
        )
        self.add_cascade(label="View", menu=view_menu)


def print_info(message: str):
    logging.info(message)


def main():
    print_info("Starting the app...")
    args = parser.parse_args()
    root = tk.Tk()
    root.title("COCO Viewer")

    if not args.images or not args.annotations:
        root.geometry("300x150")  # app size when no data is provided
        messagebox.showwarning("Warning!", "Nothing to show.\nPlease specify a path to the COCO dataset!")
        print_info("Exiting...")
        root.destroy()
        return

    data = Data(args.images, args.annotations)
    image = ImageWidget(root)
    controller = Controller(root, image, data)
    menu = Menu(root, controller)
    root.config(menu=menu)
    root.mainloop()


if __name__ == "__main__":
    main()
