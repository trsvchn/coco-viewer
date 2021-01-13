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

from PIL import Image, ImageDraw, ImageTk, ImageFont

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
        self.categories = categories  # Dataset categories
        self.img_obj_categories = None  # as list of category ids of all objects
        self.img_categories = None  # current image categories (unique sorted category ids)

        # Prepare the very first image
        self.current_image = self.images.next()  # Set the first image as current
        self.current_composed_image = None  # To store composed PIL Image

    def compose_image(
            self,
            image: tuple,
            bboxes_on: bool = True,
            labels_on: bool = True,
            masks_on: bool = True,
            ignore: list = None,
            width: int = 1,
            alpha: int = 128,
            label_size: int = 15,
    ):
        """Loads image as PIL Image and draw bboxes and/or masks.
        """
        # TODO: labels for object classes
        # TODO: predicted bboxes drawing (from models)
        img_id, img_name = image
        full_path = os.path.join(self.image_dir, img_name)
        ignore = ignore or []  # list of objects to ignore
        # Open image
        img_open = Image.open(full_path).convert("RGBA")
        # Create layer for bboxes and masks
        draw_layer = Image.new("RGBA", img_open.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(draw_layer)

        # Get objects and category ids
        objects = [obj for obj in self.instances["annotations"] if obj["image_id"] == img_id]
        obj_categories_ids = [obj["category_id"] for obj in objects]
        # Store category id of each object and unique cat ids for the image
        self.img_obj_categories = [obj["category_id"] for obj in objects]
        self.img_categories = sorted(list(set(self.img_obj_categories)))

        # Get category name - color pairs for the objects
        names_colors = [self.categories[i] for i in obj_categories_ids]

        # Draw masks
        if masks_on:
            draw_masks(draw, objects, names_colors, ignore, alpha)

        # Draw bounding boxes
        if bboxes_on:
            draw_bboxes(draw, objects, labels_on, names_colors, ignore, width, label_size)

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


def draw_bboxes(draw, objects, labels, obj_categories, ignore, width, label_size):
    """Puts rectangles on the image.
    """
    # Extracting bbox coordinates
    bboxes = [[obj["bbox"][0],
               obj["bbox"][1],
               obj["bbox"][0] + obj["bbox"][2],
               obj["bbox"][1] + obj["bbox"][3]] for obj in objects]
    # Draw bboxes
    for i, (c, b) in enumerate(zip(obj_categories, bboxes)):
        if i not in ignore:
            draw.rectangle(b, outline=c[-1], width=width)

            if labels:
                text = c[0]
                font = ImageFont.truetype("DejaVuSans.ttf", size=label_size)

                tw, th = draw.textsize(text, font)
                tx0 = b[0]
                ty0 = b[1] - th

                # TODO: Looks weird! We need image dims to make it right
                tx0 = max(b[0], max(b[0], tx0)) if tx0 < 0 else tx0
                ty0 = max(b[1], max(0, ty0)) if ty0 < 0 else ty0

                tx1 = tx0 + tw
                ty1 = ty0 + th

                # TODO: The same here
                if tx1 > b[2]:
                    tx0 = max(0, tx0 - (tx1 - b[2]))
                    tx1 = tw if tx0 == 0 else b[2]

                draw.rectangle((tx0, ty0, tx1, ty1), fill=c[-1])
                draw.text((tx0, ty0), text, (255, 255, 255), font=font)


def draw_masks(draw, objects, obj_categories, ignore, alpha):
    """Draws a masks over image.
    """
    masks = [obj["segmentation"] for obj in objects]
    # Draw masks
    for i, (c, m) in enumerate(zip(obj_categories, masks)):
        if i not in ignore:
            alpha = alpha
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


class StatusBar(tk.Frame):
    """Shows status line on the bottom.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(bg="gray75")
        self.pack(side=tk.BOTTOM, fill=tk.X)

        self.file_count = tk.Label(self, bd=5, bg="gray75")
        self.file_count.pack(side=tk.RIGHT)
        self.description = tk.Label(self, bd=5, bg="gray75")
        self.description.pack(side=tk.RIGHT)
        self.file_name = tk.Label(self, bd=5, bg="gray75")
        self.file_name.pack(side=tk.LEFT)
        self.nobjects = tk.Label(self, bd=5, bg="gray75")
        self.nobjects.pack(side=tk.LEFT)
        self.ncategories = tk.Label(self, bd=5, bg="gray75")
        self.ncategories.pack(side=tk.LEFT)


class Menu(tk.Menu):
    def __init__(self, parent):
        super().__init__(parent)
        # Define menu structure
        self.file = self.file_menu()
        self.view = self.view_menu()

    def file_menu(self):
        """File Menu.
        """
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="Save", accelerator="Ctrl+S")
        menu.add_separator()
        menu.add_command(label="Exit", accelerator="Ctrl+Q")
        self.add_cascade(label="File", menu=menu)
        return menu

    def view_menu(self):
        """View Menu.
        """
        menu = tk.Menu(self, tearoff=False)
        menu.add_checkbutton(label="BBoxes", onvalue=True, offvalue=False)
        menu.add_checkbutton(label="Labels", onvalue=True, offvalue=False)
        menu.add_checkbutton(label="Masks", onvalue=True, offvalue=False)
        self.add_cascade(label="View", menu=menu)
        return menu


class ObjectsPanel(tk.Frame):
    """Panels with listed objects and categories for the image.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(side=tk.RIGHT, fill=tk.Y)

        # Categories subpanel
        tk.Label(self, text="categories", bd=2, bg="gray50").pack(side=tk.TOP, fill=tk.X)
        self.category_box = tk.Listbox(self, selectmode=tk.EXTENDED, exportselection=0)
        self.category_box.pack(side=tk.TOP, fill=tk.Y, expand=True)

        # Objects subpanel
        tk.Label(self, text="objects", bd=2, bg="gray50").pack(side=tk.TOP, fill=tk.X)
        self.object_box = tk.Listbox(self, selectmode=tk.EXTENDED, exportselection=0)
        self.object_box.pack(side=tk.TOP, fill=tk.Y, expand=True)


class SlidersBar(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(side=tk.BOTTOM, fill=tk.X)

        # Bbox thickness controller
        self.bbox_slider = tk.Scale(self, label="bbox", from_=0, to=25, tickinterval=5, orient=tk.HORIZONTAL)
        self.bbox_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Label text size controller
        self.label_slider = tk.Scale(self, label="label", from_=10, to=100, tickinterval=25, orient=tk.HORIZONTAL)
        self.label_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Mask transparency controller
        self.mask_slider = tk.Scale(self, label="mask", from_=0, to=255, tickinterval=25, orient=tk.HORIZONTAL)
        self.mask_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)


class Controller:
    def __init__(self, data, root, image, statusbar, menu, objects_panel, sliders):
        self.data = data  # data layer
        self.root = root  # root window
        self.image = image  # image widget
        self.statusbar = statusbar  # statusbar on the bottom
        self.menu = menu  # main menu on the top
        self.objects_panel = objects_panel
        self.sliders = sliders

        # StatusBar Vars
        self.file_count_status = tk.StringVar()
        self.file_name_status = tk.StringVar()
        self.description_status = tk.StringVar()
        self.nobjects_status = tk.StringVar()
        self.ncategories_status = tk.StringVar()
        self.statusbar.file_count.configure(textvariable=self.file_count_status)
        self.statusbar.file_name.configure(textvariable=self.file_name_status)
        self.statusbar.description.configure(textvariable=self.description_status)
        self.statusbar.nobjects.configure(textvariable=self.nobjects_status)
        self.statusbar.ncategories.configure(textvariable=self.ncategories_status)

        # Menu Vars
        self.bboxes_on_global = tk.BooleanVar()  # Toggles bboxes globally
        self.bboxes_on_global.set(True)
        self.labels_on_global = tk.BooleanVar()  # Toggles category labels
        self.labels_on_global.set(True)
        self.masks_on_global = tk.BooleanVar()  # Toggles masks globally
        self.masks_on_global.set(True)
        # Menu Configuration
        self.menu.file.entryconfigure("Save", command=self.save_image)
        self.menu.file.entryconfigure("Exit", command=self.exit)
        self.menu.view.entryconfigure("BBoxes", variable=self.bboxes_on_global, command=self.update_img)
        self.menu.view.entryconfigure("Labels", variable=self.labels_on_global, command=self.update_img)
        self.menu.view.entryconfigure("Masks", variable=self.masks_on_global, command=self.update_img)
        self.root.configure(menu=self.menu)

        # Init local setup (for the current (active) image)
        self.bboxes_on_local = self.bboxes_on_global.get()
        self.labels_on_local = self.labels_on_global.get()
        self.masks_on_local = self.masks_on_global.get()

        # Objects Panel stuff
        self.selected_cats = None
        self.selected_objs = None
        self.category_box_content = tk.StringVar()
        self.object_box_content = tk.StringVar()
        self.objects_panel.category_box.configure(listvariable=self.category_box_content)
        self.objects_panel.object_box.configure(listvariable=self.object_box_content)

        # Sliders Setup
        self.bbox_thickness = tk.IntVar()
        self.bbox_thickness.set(3)
        self.label_size = tk.IntVar()
        self.label_size.set(15)
        self.mask_alpha = tk.IntVar()
        self.mask_alpha.set(128)
        self.sliders.bbox_slider.configure(variable=self.bbox_thickness, command=lambda e: self.update_img())
        self.sliders.label_slider.configure(variable=self.label_size, command=lambda e: self.update_img())
        self.sliders.mask_slider.configure(variable=self.mask_alpha, command=lambda e: self.update_img())

        # Bind all events
        self.bind_events()

        # Compose the very first image
        self.update_img()

    def update_img(
            self,
            bboxes_on=None,
            labels_on=None,
            masks_on=None,
            width=None,
            alpha=None,
            label_size=None,
    ):
        """Triggers image composition and sets composed image as current.
        """
        self.bboxes_on_local = self.bboxes_on_global.get() if bboxes_on is None else bboxes_on
        self.labels_on_local = self.labels_on_global.get() if labels_on is None else labels_on
        self.masks_on_local = self.masks_on_global.get() if masks_on is None else masks_on

        if self.selected_objs is None:
            ignore = []
        else:
            ignore = [i for i in range(len(self.data.img_obj_categories)) if i not in self.selected_objs]

        width = self.bbox_thickness.get() if width is None else width
        alpha = self.mask_alpha.get() if alpha is None else alpha
        label_size = self.label_size.get() if label_size is None else label_size

        # Compose image
        self.data.compose_current_image(
            bboxes_on=self.bboxes_on_local,
            labels_on=self.labels_on_local,
            masks_on=self.masks_on_local,
            ignore=ignore,
            width=width,
            alpha=alpha,
            label_size=label_size,
        )

        # Prepare PIL image for Tkinter
        img = self.data.current_composed_image
        img = ImageTk.PhotoImage(img)

        # Set image as current
        self.image.image.configure(image=img)
        self.image.image.image = img

        # Update statusbar vars
        self.file_count_status.set(f"{str(self.data.images.n + 1)}/{self.data.images.max}")
        self.file_name_status.set(f"{self.data.current_image[-1]}")
        self.description_status.set(f"{self.data.instances.get('info', '').get('description', '')}")
        self.nobjects_status.set(f"objects: {len(self.data.img_obj_categories)}")
        self.ncategories_status.set(f"categories: {len(self.data.img_categories)}")

        # Update Objects panel
        self.update_category_box()
        self.update_object_box()

    def exit(self, event=None):
        print_info("Exiting...")
        self.root.quit()

    def next_img(self, event=None):
        self.data.next_image()
        self.selected_cats = None
        self.selected_objs = None
        self.update_img()

    def prev_img(self, event=None):
        self.data.previous_image()
        self.selected_cats = None
        self.selected_objs = None
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
            self.data.current_composed_image.save(file)

    def toggle_bboxes(self, event=None):
        self.bboxes_on_local = not self.bboxes_on_local
        self.update_img(bboxes_on=self.bboxes_on_local)

    def toggle_labels(self, event=None):
        self.labels_on_local = not self.labels_on_local
        self.update_img(labels_on=self.labels_on_local)

    def toggle_masks(self, event=None):
        self.masks_on_local = not self.masks_on_local
        self.update_img(masks_on=self.masks_on_local)

    def toggle_all(self, event=None):
        # Toggle only when focused on image
        if event.widget.focus_get() is self.objects_panel.category_box:
            return
        if event.widget.focus_get() is self.objects_panel.object_box:
            return
        # What to toggle
        var_list = [self.bboxes_on_local, self.masks_on_local]
        # if any is on, turn them off
        if True in set(var_list):
            self.bboxes_on_local = False
            self.masks_on_local = False
        # if all is off, turn them on
        else:
            self.bboxes_on_local = True
            self.masks_on_local = True
        # Update image with updated vars
        self.update_img(bboxes_on=self.bboxes_on_local, masks_on=self.masks_on_local)

    def update_category_box(self):
        ids = self.data.img_categories
        names = [self.data.categories[i][0] for i in ids]
        self.category_box_content.set([" ".join([str(i), str(n)]) for i, n in zip(ids, names)])
        self.objects_panel.category_box.selection_clear(0, tk.END)
        if self.selected_cats is not None:
            for i in self.selected_cats:
                self.objects_panel.category_box.select_set(i)
        else:
            self.objects_panel.category_box.select_set(0, tk.END)

    def select_category(self, event):
        # Get selection from user
        selected_ids = self.objects_panel.category_box.curselection()
        # Set selected_cats
        self.selected_cats = selected_ids
        # Set selected_objs
        selected_objs = []
        for ci in self.selected_cats:
            for i, o in enumerate(self.data.img_obj_categories):
                if self.data.img_categories[ci] == o:
                    selected_objs.append(i)
        self.selected_objs = selected_objs
        self.update_img()

    def update_object_box(self):
        ids = self.data.img_obj_categories
        names = [self.data.categories[i][0] for i in ids]
        self.object_box_content.set([" ".join([str(i), str(n)]) for i, n in enumerate(names)])
        self.objects_panel.object_box.selection_clear(0, tk.END)
        if self.selected_objs is not None:
            for i in self.selected_objs:
                self.objects_panel.object_box.select_set(i)
        else:
            self.objects_panel.object_box.select_set(0, tk.END)

    def select_object(self, event):
        # Get selection from user
        selected_ids = self.objects_panel.object_box.curselection()
        # Set selected_cats
        self.selected_objs = selected_ids
        # Set selected_objs
        selected_cats = []
        for oi in self.selected_objs:
            for i, c in enumerate(self.data.img_categories):
                if self.data.img_obj_categories[oi] == c:
                    selected_cats.append(i)
        self.selected_cats = selected_cats
        self.update_img()

    def bind_events(self):
        """Binds events.
        """
        # Navigation
        self.root.bind("<Left>", self.prev_img)
        self.root.bind("<k>", self.prev_img)
        self.root.bind("<Right>", self.next_img)
        self.root.bind("<j>", self.next_img)
        self.root.bind("<Control-q>", self.exit)
        self.root.bind("<Control-w>", self.exit)

        # Files
        self.root.bind("<Control-s>", self.save_image)

        # View Toggles
        self.root.bind("<b>", self.toggle_bboxes)
        self.root.bind("<Control-b>", self.toggle_bboxes)
        self.root.bind("<l>", self.toggle_labels)
        self.root.bind("<Control-l>", self.toggle_labels)
        self.root.bind("<m>", self.toggle_masks)
        self.root.bind("<Control-m>", self.toggle_masks)
        self.root.bind("<space>", self.toggle_all)

        # Objects Panel
        self.objects_panel.category_box.bind('<<ListboxSelect>>', self.select_category)
        self.objects_panel.object_box.bind('<<ListboxSelect>>', self.select_object)
        self.image.image.bind("<Button-1>", lambda e: self.image.focus_set())


def print_info(message: str):
    logging.info(message)


def main():
    print_info("Starting...")
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
    statusbar = StatusBar(root)
    sliders = SlidersBar(root)
    objects_panel = ObjectsPanel(root)
    menu = Menu(root)
    image = ImageWidget(root)
    Controller(data, root, image, statusbar, menu, objects_panel, sliders)
    root.mainloop()


if __name__ == "__main__":
    main()
