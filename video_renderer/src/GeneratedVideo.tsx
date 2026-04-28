import {
  AbsoluteFill,
  Img,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export type VideoScene = {
  index: number;
  title: string;
  narration: string;
  visual_prompt: string;
  on_screen_text: string;
  duration_seconds: number;
  image_url?: string | null;
};

export type VideoInput = {
  jobId: number;
  prompt: string;
  style: string;
  durationSeconds: number;
  fps: number;
  width: number;
  height: number;
  aspectRatio: string;
  scenes: VideoScene[];
  sources: Array<{title: string; url: string; snippet: string}>;
};

export const defaultVideoInput: VideoInput = {
  jobId: 0,
  prompt: 'AI agents coordinating work',
  style: 'educational',
  durationSeconds: 15,
  fps: 30,
  width: 1280,
  height: 720,
  aspectRatio: '16:9',
  scenes: [
    {
      index: 1,
      title: 'Opening',
      narration: 'Introduce the idea with a clear hook.',
      visual_prompt: 'Modern abstract technology scene',
      on_screen_text: 'AI agents, working together',
      duration_seconds: 5,
    },
    {
      index: 2,
      title: 'Middle',
      narration: 'Show the main benefits and motion.',
      visual_prompt: 'Connected interfaces and workflows',
      on_screen_text: 'Plan, research, create',
      duration_seconds: 5,
    },
    {
      index: 3,
      title: 'Close',
      narration: 'End with a concise takeaway.',
      visual_prompt: 'Polished product-style ending frame',
      on_screen_text: 'From prompt to output',
      duration_seconds: 5,
    },
  ],
  sources: [],
};

const palettes: Record<string, string[]> = {
  cinematic: ['#07110f', '#1d4f68', '#d7b56d'],
  educational: ['#0b1110', '#12824f', '#d8f3dc'],
  product_demo: ['#101828', '#2563eb', '#dbeafe'],
  social_short: ['#111827', '#db2777', '#fef3c7'],
  slideshow: ['#172033', '#64748b', '#f8fafc'],
};

const scenePalettes = [
  ['#0b1110', '#12824f', '#d8f3dc'],
  ['#111827', '#2563eb', '#fef3c7'],
  ['#160f29', '#db2777', '#f5d0fe'],
  ['#102a43', '#0ea5e9', '#cffafe'],
  ['#1c1917', '#d97706', '#ffedd5'],
  ['#111827', '#7c3aed', '#ddd6fe'],
  ['#042f2e', '#14b8a6', '#ccfbf1'],
  ['#1f2937', '#ef4444', '#fee2e2'],
];

const getSceneAtFrame = (scenes: VideoScene[], frame: number, fps: number) => {
  let start = 0;
  for (const scene of scenes) {
    const frames = Math.max(1, Math.round(scene.duration_seconds * fps));
    if (frame < start + frames) {
      return {scene, localFrame: frame - start, sceneFrames: frames};
    }
    start += frames;
  }

  const last = scenes[scenes.length - 1] ?? defaultVideoInput.scenes[0];
  return {
    scene: last,
    localFrame: 0,
    sceneFrames: Math.max(1, Math.round(last.duration_seconds * fps)),
  };
};

export const GeneratedVideo = (props: VideoInput) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const scenes = props.scenes.length > 0 ? props.scenes : defaultVideoInput.scenes;
  const {scene, localFrame, sceneFrames} = getSceneAtFrame(scenes, frame, fps);
  const basePalette = palettes[props.style] ?? palettes.educational;
  const scenePalette = scenePalettes[(scene.index - 1) % scenePalettes.length] ?? basePalette;
  const palette = scene.image_url ? scenePalette : basePalette;
  const progress = interpolate(localFrame, [0, sceneFrames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const textOpacity = interpolate(localFrame, [0, 12, sceneFrames - 12, sceneFrames], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const scale = interpolate(progress, [0, 1], [1.05, 1.16]);
  const imageX = interpolate(progress, [0, 1], [-18, 18]);
  const imageY = interpolate(progress, [0, 1], [10, -10]);
  const isVertical = height > width;

  return (
    <AbsoluteFill
      style={{
        overflow: 'hidden',
        background: `linear-gradient(135deg, ${palette[0]} 0%, ${palette[1]} 54%, ${palette[2]} 140%)`,
        color: 'white',
        fontFamily: 'Inter, Arial, sans-serif',
      }}
    >
      {scene.image_url ? (
        <Img
          src={scene.image_url}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            opacity: 0.72,
            filter: 'saturate(1.14) contrast(1.06)',
            transform: `translate(${imageX}px, ${imageY}px) scale(${scale})`,
          }}
        />
      ) : null}

      {scene.image_url ? (
        <>
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background:
                'linear-gradient(90deg, rgba(0,0,0,0.68) 0%, rgba(0,0,0,0.38) 48%, rgba(0,0,0,0.16) 100%)',
            }}
          />
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: `linear-gradient(135deg, ${palette[0]}88 0%, transparent 46%, ${palette[1]}55 100%)`,
              mixBlendMode: 'multiply',
            }}
          />
        </>
      ) : null}

      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            `radial-gradient(circle at 20% 18%, ${palette[2]}44, transparent 28%), radial-gradient(circle at 88% 72%, rgba(255,255,255,0.18), transparent 32%)`,
          transform: `translateX(${progress * 24}px) scale(${scale})`,
        }}
      />

      <div
        style={{
          position: 'absolute',
          top: isVertical ? 40 : 54,
          right: isVertical ? 34 : 58,
          width: isVertical ? 92 : 128,
          height: isVertical ? 92 : 128,
          borderRadius: 999,
          border: '2px solid rgba(255,255,255,0.42)',
          opacity: 0.7,
          transform: `rotate(${progress * 90}deg) scale(${1 + progress * 0.12})`,
        }}
      />

      <div
        style={{
          position: 'absolute',
          left: isVertical ? 44 : 76,
          right: isVertical ? 44 : 76,
          bottom: isVertical ? 96 : 76,
          opacity: textOpacity,
        }}
      >
        <div
          style={{
            fontSize: isVertical ? 28 : 30,
            fontWeight: 700,
            marginBottom: 18,
            color: 'rgba(255,255,255,0.78)',
            textShadow: '0 12px 30px rgba(0,0,0,0.35)',
          }}
        >
          {String(scene.title || `Scene ${scene.index}`).toUpperCase()}
        </div>
        <div
          style={{
            fontSize: isVertical ? 54 : 70,
            lineHeight: 1.05,
            fontWeight: 800,
            maxWidth: isVertical ? 620 : 980,
            letterSpacing: 0,
            textShadow: '0 22px 60px rgba(0,0,0,0.42)',
          }}
        >
          {scene.on_screen_text || props.prompt}
        </div>
        <div
          style={{
            marginTop: 28,
            width: `${Math.max(12, progress * 100)}%`,
            height: 7,
            borderRadius: 999,
            background: 'rgba(255,255,255,0.82)',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
