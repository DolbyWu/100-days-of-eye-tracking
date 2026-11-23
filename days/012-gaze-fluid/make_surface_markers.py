"""Generate a transparent TouchDesigner AprilTag overlay and geometry JSON."""
import argparse
import json
from pathlib import Path


def generate(width=1200, height=815, side=88, margin=20, quiet=12):
    import cv2
    import numpy as np
    dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    outer = side + 2*quiet
    if min(width, height) <= 2*(outer+margin):
        raise ValueError("Canvas is too small for four markers")
    image = np.zeros((height,width,4),dtype=np.uint8)
    locations = [(margin,margin),(width-margin-outer,margin),
                 (width-margin-outer,height-margin-outer),(margin,height-margin-outer)]
    layout = {"size":[width,height],"markers":{}}
    for tag_id,(ox,oy) in enumerate(locations):
        image[oy:oy+outer,ox:ox+outer] = (255,255,255,255)
        marker = dictionary.generateImageMarker(tag_id,side,0)
        image[oy+quiet:oy+quiet+side,ox+quiet:ox+quiet+side,:3] = marker[:,:,None]
        x,y=ox+quiet,oy+quiet
        layout["markers"][str(tag_id)] = [[x,y],[x+side,y],[x+side,y+side],[x,y+side]]
    return image,layout


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width",type=int,default=1200)
    parser.add_argument("--height",type=int,default=815)
    parser.add_argument("--output",type=Path,default=Path(__file__).parent/"media")
    args=parser.parse_args()
    import cv2
    image,layout=generate(args.width,args.height)
    args.output.mkdir(parents=True,exist_ok=True)
    png=args.output/"surface-markers.png"
    geo=args.output/"surface-layout.json"
    if not cv2.imwrite(str(png),image):
        raise OSError(f"Could not write {png}")
    geo.write_text(json.dumps(layout,indent=2)+"\n",encoding="utf-8")
    print(png)
    print(geo)


if __name__=="__main__":
    main()
