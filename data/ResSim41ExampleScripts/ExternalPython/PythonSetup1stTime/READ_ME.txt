Step 1

Move the Miniconda3 zip file to a folder on you C drive. If you already have a folder for mobile programs, put it there. If you don't have a mobile programs folder or equivalent, make one and put it there. Unzip it there and run it. You want to install for ALL USERS (Important). 

Step 2

Search Anaconda in Windows and open Anaconda Prompt, then paste conda env create -f followed by a space, then drag the hydro39.yml file into the console to copy the path over. then hit enter. This takes a long time (about 20 min) but should run in the background fine. to see that its still installing and not hanging you can go to the environment and check the properties of the folder to see the size, then check again in a minute. If it's bigger, it's still working. "C:\Users\g2encjer\AppData\Local\miniconda3\envs\Conservation" with your user name. The final file size for me was 1,883.9 MB.

*** NOTE *** This environment may be a little bloated, but it works. Getting an environment that works with pydsstools and newer packages is a bit of a pain making it worth it to live with the bloat here.

