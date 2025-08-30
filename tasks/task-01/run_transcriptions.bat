@echo off
echo Running Basic Pitch transcriptions on all samples...

echo.
echo [1/3] Transcribing clean studio sample...
call conda activate pianoscribe
call basic-pitch tasks/task-01/outputs/sample tasks/task-01/samples/sample.mp3

echo.
echo [2/3] Transcribing live piano sample with noise...
call basic-pitch tasks/task-01/outputs/live_piano tasks/task-01/samples/live_piano.mp3

echo.
echo [3/3] Transcribing YouTube piano sample...
call basic-pitch tasks/task-01/outputs/youtube_piano tasks/task-01/samples/youtube_piano.mp3

echo.
echo All transcriptions complete!
echo Check tasks/task-01/outputs/ for results.