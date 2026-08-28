"""
Shared video reader for all detectors.

Version 1:
    - OpenCV backend
    - Unified interface

Future versions:
    - FFmpeg backend
    - Hardware decoding
    - Smart frame sampling
    - Frame cache
"""

from dataclasses import dataclass

import cv2



@dataclass
class VideoFrame:

    image: any

    index: int

    timestamp: float






@dataclass
class VideoInfo:

    width: int

    height: int

    fps: float

    frame_count: int

    duration: float


class VideoReader:

    def __init__(self, video_path):

        self.video_path = video_path

        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():

            raise RuntimeError(
                f"Unable to open video: {video_path}"
            )

        self.info = VideoInfo(

            width=int(
                self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            ),

            height=int(
                self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            ),

            fps=self.cap.get(
                cv2.CAP_PROP_FPS
            ),

            frame_count=int(
                self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            ),

            duration=0.0

        )

        if self.info.fps > 0:

            self.info.duration = (
                self.info.frame_count /
                self.info.fps
            )

    def __iter__(self):

        while True:

            ret, frame = self.cap.read()

            if not ret:
                break

            frame_index = self.current_frame()

            yield VideoFrame(
                image=frame,
                index=frame_index,
                timestamp=(
                    frame_index / self.info.fps
                    if self.info.fps > 0
                    else 0.0
                )
            )




    def iter_sampled(self, frame_step):

        frame_index = 0

        while True:

            if frame_index % frame_step == 0:

                if not self.cap.grab():
                    break

                ret, frame = self.cap.retrieve()

                if not ret:
                    break

                #self._current_frame = frame

                yield VideoFrame(
                    image=frame,
                    index=frame_index,
                    timestamp=(
                        frame_index / self.info.fps
                        if self.info.fps > 0 else 0.0
                    )
                )

            else:

                if not self.cap.grab():
                    break

            frame_index += 1



    def seek_frame(self, frame_index):

        self.cap.set(
            cv2.CAP_PROP_POS_FRAMES,
            frame_index
        )

    def current_frame(self):

        return int(
            self.cap.get(
                cv2.CAP_PROP_POS_FRAMES
            )
        )

    def release(self):

        self.cap.release()

    def __enter__(self):

        return self

    def __exit__(self, exc_type, exc, tb):

        self.release()




    @property
    def fps(self):
        return self.info.fps

    @property
    def frame_count(self):
        return self.info.frame_count

    @property
    def duration(self):
        return self.info.duration