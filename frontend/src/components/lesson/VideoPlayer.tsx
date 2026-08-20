"use client";

import { useRef } from "react";
import type { Video } from "@/types";

interface VideoPlayerProps {
  video: Video;
  resumeSeconds?: number | null;
  onProgress?: (positionSeconds: number, durationSeconds: number) => void;
  onEnded?: () => void;
}

const SAVE_INTERVAL_SECONDS = 10;

export function VideoPlayer({ video, resumeSeconds, onProgress, onEnded }: VideoPlayerProps) {
  const lastSavedAt = useRef(0);

  if (!video.playback_url) {
    return (
      <div className="flex aspect-video items-center justify-center rounded-xl bg-slate-100 text-sm text-slate-500">
        Video coming soon.
      </div>
    );
  }

  if (video.provider === "youtube_unlisted") {
    return (
      <div className="aspect-video overflow-hidden rounded-xl bg-black">
        <iframe
          src={video.playback_url}
          className="h-full w-full"
          title="Lesson video"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    );
  }

  return (
    <video
      className="aspect-video w-full rounded-xl bg-black"
      src={video.playback_url}
      controls
      onLoadedMetadata={(e) => {
        if (resumeSeconds) e.currentTarget.currentTime = resumeSeconds;
      }}
      onTimeUpdate={(e) => {
        const t = e.currentTarget.currentTime;
        if (t - lastSavedAt.current >= SAVE_INTERVAL_SECONDS) {
          lastSavedAt.current = t;
          onProgress?.(t, e.currentTarget.duration || 0);
        }
      }}
      onPause={(e) => onProgress?.(e.currentTarget.currentTime, e.currentTarget.duration || 0)}
      onEnded={onEnded}
    >
      Your browser doesn&apos;t support embedded video.
    </video>
  );
}
