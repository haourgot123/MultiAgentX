import {
  AbsoluteFill,
  Easing,
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
  ['#e8f4ff', '#8cd5ff', '#0c57c6'],
  ['#f8fcff', '#9ce1f9', '#0b75d1'],
  ['#edf7ff', '#78d5ff', '#0f4fbf'],
  ['#f5fbff', '#b0e4ff', '#135cc9'],
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
  const scenePalette = scenePalettes[(scene.index - 1) % scenePalettes.length] ?? ['#eef8ff', '#96dbff', '#0d57c5'];
  const palette = scenePalette ?? basePalette;
  const progress = interpolate(localFrame, [0, sceneFrames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const easedProgress = interpolate(progress, [0, 1], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.22, 1, 0.36, 1),
  });
  const textOpacity = interpolate(localFrame, [0, 12, sceneFrames - 12, sceneFrames], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const textSlide = interpolate(easedProgress, [0, 1], [44, 0]);
  const cardSlide = interpolate(easedProgress, [0, 1], [90, 0]);
  const cardFloat = Math.sin((localFrame / sceneFrames) * Math.PI * 2) * 12;
  const ringRotate = interpolate(easedProgress, [0, 1], [0, 55]);
  const shineX = interpolate(easedProgress, [0, 1], [-220, 340]);
  const isVertical = height > width;
  const cartonWidth = isVertical ? 250 : 300;
  const cartonHeight = isVertical ? 420 : 510;
  const benefitBadges = ['Canxi', 'Protein', 'Tươi mát'];
  const sceneLabel = String(scene.title || `Scene ${scene.index}`).toUpperCase();
  const headline = scene.on_screen_text || props.prompt;
  const subline = scene.narration || 'Nguon dinh duong tuoi ngon cho ca nha.';

  return (
    <AbsoluteFill
      style={{
        overflow: 'hidden',
        background: `linear-gradient(135deg, ${palette[0]} 0%, ${palette[1]} 42%, #d7f1ff 75%, #f9fdff 100%)`,
        color: '#0b3c8b',
        fontFamily: '"Avenir Next", "Montserrat", Arial, sans-serif',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(circle at 15% 20%, rgba(255,255,255,0.95), transparent 24%), radial-gradient(circle at 80% 18%, rgba(122,214,255,0.42), transparent 21%), radial-gradient(circle at 82% 78%, rgba(12,87,198,0.14), transparent 24%)',
        }}
      />

      <div
        style={{
          position: 'absolute',
          left: isVertical ? -120 : -80,
          right: isVertical ? -120 : -80,
          bottom: isVertical ? -120 : -150,
          height: isVertical ? 320 : 260,
          background:
            'linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.86) 25%, rgba(255,255,255,1) 100%)',
          borderTopLeftRadius: '50% 100%',
          borderTopRightRadius: '50% 100%',
          transform: `translateY(${Math.sin(frame / 18) * 10}px)`,
        }}
      />

      <div
        style={{
          position: 'absolute',
          top: isVertical ? 52 : 48,
          left: isVertical ? 34 : 58,
          padding: isVertical ? '10px 18px' : '12px 20px',
          borderRadius: 999,
          background: 'rgba(255,255,255,0.78)',
          border: '1px solid rgba(11,87,198,0.12)',
          color: '#0c57c6',
          fontSize: isVertical ? 24 : 22,
          fontWeight: 800,
          letterSpacing: 1.5,
        }}
      >
        VINAMILK
      </div>

      <div
        style={{
          position: 'absolute',
          top: isVertical ? 130 : 126,
          left: isVertical ? 34 : 58,
          width: isVertical ? width - 68 : width * 0.5,
          opacity: textOpacity,
          transform: `translateX(${textSlide}px)`,
        }}
      >
        <div
          style={{
            fontSize: isVertical ? 24 : 20,
            fontWeight: 800,
            color: '#0a72d5',
            letterSpacing: 2.6,
            marginBottom: 18,
          }}
        >
          {sceneLabel}
        </div>
        <div
          style={{
            fontSize: isVertical ? 72 : 78,
            lineHeight: 0.98,
            fontWeight: 900,
            color: '#0b3c8b',
            maxWidth: isVertical ? '100%' : 620,
            textShadow: '0 14px 32px rgba(90,165,255,0.16)',
          }}
        >
          {headline}
        </div>
        <div
          style={{
            marginTop: 22,
            fontSize: isVertical ? 28 : 26,
            lineHeight: 1.38,
            fontWeight: 600,
            color: 'rgba(11,60,139,0.82)',
            maxWidth: isVertical ? '100%' : 590,
          }}
        >
          {subline}
        </div>
        <div
          style={{
            display: 'flex',
            gap: 14,
            marginTop: 28,
            flexWrap: 'wrap',
          }}
        >
          {benefitBadges.map((badge, index) => (
            <div
              key={`${badge}-${index}`}
              style={{
                padding: isVertical ? '10px 16px' : '10px 18px',
                borderRadius: 999,
                background: 'rgba(255,255,255,0.82)',
                border: '1px solid rgba(11,87,198,0.12)',
                color: '#0b5bc8',
                fontWeight: 800,
                fontSize: isVertical ? 22 : 18,
              }}
            >
              {badge}
            </div>
          ))}
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          right: isVertical ? 46 : 88,
          top: isVertical ? 290 : 112,
          width: cartonWidth + 120,
          height: cartonHeight + 120,
          transform: `translateX(${cardSlide}px) translateY(${cardFloat}px)`,
          opacity: textOpacity,
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: 999,
            border: '3px solid rgba(11,87,198,0.14)',
            transform: `rotate(${ringRotate}deg)`,
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: 40,
            borderRadius: 999,
            border: '2px dashed rgba(24,148,255,0.22)',
            transform: `rotate(${-ringRotate * 1.35}deg)`,
          }}
        />
        <div
          style={{
            position: 'absolute',
            right: 24,
            top: 18,
            width: 54,
            height: 54,
            borderRadius: 999,
            background: 'rgba(255,255,255,0.96)',
            boxShadow: '0 20px 40px rgba(12,87,198,0.12)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: 28,
            bottom: 28,
            width: 34,
            height: 34,
            borderRadius: 999,
            background: 'rgba(145,225,255,0.72)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: 74,
            top: 82,
            width: cartonWidth,
            height: cartonHeight,
            borderRadius: 36,
            overflow: 'hidden',
            boxShadow: '0 34px 80px rgba(7,79,175,0.24)',
            background: 'linear-gradient(180deg, #ffffff 0%, #f0f9ff 100%)',
            border: '1px solid rgba(12,87,198,0.08)',
          }}
        >
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: 0,
              height: 132,
              background: 'linear-gradient(135deg, #0d57c5 0%, #16a7f4 100%)',
            }}
          />
          <div
            style={{
              position: 'absolute',
              top: 0,
              right: -30,
              width: 140,
              height: 132,
              background: 'rgba(255,255,255,0.18)',
              transform: 'skewX(-28deg)',
            }}
          />
          <div
            style={{
              position: 'absolute',
              top: 28,
              left: 28,
              color: '#ffffff',
              fontWeight: 900,
              fontSize: 34,
              letterSpacing: 1.5,
            }}
          >
            VINAMILK
          </div>
          <div
            style={{
              position: 'absolute',
              top: 176,
              left: 30,
              width: 136,
              height: 136,
              borderRadius: 999,
              background: 'linear-gradient(180deg, #ffffff 0%, #d8f0ff 100%)',
              border: '10px solid #8fd4ff',
            }}
          />
          <div
            style={{
              position: 'absolute',
              top: 196,
              left: 64,
              color: '#0d57c5',
              fontSize: 50,
              fontWeight: 900,
            }}
          >
            100%
          </div>
          <div
            style={{
              position: 'absolute',
              top: 176,
              right: 28,
              left: 190,
              color: '#0b3c8b',
              fontWeight: 900,
              fontSize: 32,
              lineHeight: 1.1,
            }}
          >
            SUA
            <br />
            TUOI
          </div>
          <div
            style={{
              position: 'absolute',
              left: 30,
              right: 30,
              bottom: 120,
              height: 78,
              background:
                'linear-gradient(180deg, rgba(130,211,255,0.2) 0%, rgba(12,87,198,0.08) 100%)',
              borderRadius: 22,
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: 32,
              right: 32,
              bottom: 38,
              color: '#0a5cca',
              fontWeight: 800,
              fontSize: 27,
              textAlign: 'center',
              letterSpacing: 0.8,
            }}
          >
            TUOI NGON MOI NGAY
          </div>
          <div
            style={{
              position: 'absolute',
              top: -24,
              left: shineX,
              width: 90,
              height: cartonHeight + 80,
              transform: 'rotate(14deg)',
              background: 'linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.78) 50%, rgba(255,255,255,0) 100%)',
              opacity: 0.6,
            }}
          />
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          left: isVertical ? 34 : 58,
          right: isVertical ? 34 : 58,
          bottom: isVertical ? 38 : 32,
          height: 10,
          borderRadius: 999,
          background: 'rgba(11,87,198,0.12)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${Math.max(8, easedProgress * 100)}%`,
            height: '100%',
            borderRadius: 999,
            background: 'linear-gradient(90deg, #0d57c5 0%, #19b6ff 100%)',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
