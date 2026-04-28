import {Composition, registerRoot} from 'remotion';
import {GeneratedVideo, defaultVideoInput, type VideoInput} from './GeneratedVideo';

const RemotionRoot = () => {
  return (
    <Composition<VideoInput>
      id="GeneratedVideo"
      component={GeneratedVideo}
      durationInFrames={defaultVideoInput.durationSeconds * defaultVideoInput.fps}
      fps={defaultVideoInput.fps}
      width={defaultVideoInput.width}
      height={defaultVideoInput.height}
      defaultProps={defaultVideoInput}
      calculateMetadata={({props}) => ({
        durationInFrames: Math.max(1, Math.round(props.durationSeconds * props.fps)),
        fps: props.fps,
        width: props.width,
        height: props.height,
      })}
    />
  );
};

registerRoot(RemotionRoot);
