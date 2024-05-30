# Image Viewer Row Column (imva\_rc)

This allows you to view images in a confusion matrix style format. 

## Usage 

```
python3 -m pip install -e .
python3 -m imva_rc --image_directory `pwd` --ip img_{r:rnum}_{c:cnum}.png --port 7863 --cp portrait_{num}.png --rp bg_{num}.png
```

In my case, my folder had files named `img_1_1.png, img_1_2.png ...` and I got:  

![image](https://github.com/Vrroom/imva_rc/assets/7254326/1e43f3b3-64a1-4f1d-9012-71a15c3d0c1f)
