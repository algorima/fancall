import type { VideoRegion } from "@/schemas";

export interface Size {
  width: number;
  height: number;
}

export interface Rect extends Size {
  left: number;
  top: number;
}

/**
 * Screen rectangle of `region` once a photo of `photoAspect` (width / height)
 * is drawn with `object-cover` (centered) into `container`.
 */
export const coverRegionRect = (
  container: Size,
  photoAspect: number,
  region: VideoRegion,
): Rect => {
  const scale = Math.max(container.width / photoAspect, container.height);
  const photo = { width: photoAspect * scale, height: scale };
  const offsetLeft = (container.width - photo.width) / 2;
  const offsetTop = (container.height - photo.height) / 2;
  return {
    left: offsetLeft + region.x * photo.width,
    top: offsetTop + region.y * photo.height,
    width: region.width * photo.width,
    height: region.height * photo.height,
  };
};

/**
 * Photo aspect implied by a region that holds video of `videoAspect`:
 * (region.width * photoWidth) / (region.height * photoHeight) = videoAspect
 */
export const photoAspectFromRegion = (
  region: VideoRegion,
  videoAspect: number,
) => (videoAspect * region.height) / region.width;
