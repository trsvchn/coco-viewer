# Local COCO Viewer

> Simple COCO Objects Viewer in Tkinter. Allows quick viewing on local machine.

![Example images](examples/example.jpg)

## Requirements
`python3` `PIL`

## Installation

```
git clone https://github.com/tsavchyn/local-coco-viewer.git
```

## Usage

```bash
python cocoviewer.py -h

usage: cocoviewer.py [-h] [-i PATH] [-a PATH]

View images with bboxes from COCO dataset

optional arguments:
  -h, --help                    show this help message and exit
  -i PATH, --images PATH        path to images folder
  -a PATH, --annotations PATH   path to annotations json file
```

## Example:

```bash
python cocoviewer.py -i coco/images/val/val2017 -a coco/annotations/val/instances_val2017.json
```

## TODOs

- [ ] Class labels
- [ ] Predicted bboxes (to compare with ground truths)
- [ ] More navigating options
- [ ] Add export image option (with all bboex and masks)
- [ ] RLE masks
- [ ] Keypoints
