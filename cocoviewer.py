"""Run module
"""
import argparse
from app import App

parser = argparse.ArgumentParser(description='View images with bboxes from COCO dataset')
parser.add_argument('-i', '--images', default='', type=str, metavar='PATH', help='path to images folder')
parser.add_argument('-a', '--annotations', default='', type=str, metavar='PATH', help='path to annotations json file')


def main():
    args = parser.parse_args()
    app = App(args.images, args.annotations)
    app.mainloop()


if __name__ == "__main__":
    main()
