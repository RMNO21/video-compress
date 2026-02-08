# video-compress
compress video size and decrease the size to 1/4 of the original size with smart algorithm 



I started by developing a script to split an image into two distinct checkerboard grids based on even and odd pixel coordinates.

To maintain the original image dimensions, I moved away from resizing and instead experimented with filling the gaps with solid black or white pixels.

I refined the logic by using spatial averaging to fill the removed pixels, making the transitions smoother and more natural.

To fix the "halo" effect and blurring at sharp edges, I created a selective mean algorithm that analyzes four neighbors, discards the most different one, and averages the remaining three.

I scaled the entire process to video, ensuring that the pixel grids alternate every single frame at 30 FPS to create a high-frequency temporal reconstruction.
