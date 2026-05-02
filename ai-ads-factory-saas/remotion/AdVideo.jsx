export function AdVideo(props) {
  const isAfter = true;
  const blur = "none";
  const scale = 1;

  return (
    <div style={{ position: "absolute", inset: 0, background: props.primary, color: "white", padding: 70 }}>
      <h1 style={{ fontSize: 74, fontWeight: 900, lineHeight: 1.05 }}>
        {isAfter ? props.headline : props.hook}
      </h1>

      <div
        style={{
          marginTop: 80,
          height: 1120,
          borderRadius: 42,
          transform: `scale(${scale})`,
          filter: blur,
          background: isAfter
            ? `linear-gradient(135deg, ${props.accent}, ${props.highlight})`
            : "linear-gradient(135deg,#64748B,#1E293B)",
          boxShadow: `0 40px 120px ${props.accent}66`
        }}
      />

      <div style={{
        position: "absolute",
        bottom: 90,
        left: 70,
        right: 70,
        background: props.accent,
        borderRadius: 24,
        padding: 32,
        textAlign: "center",
        fontSize: 42,
        fontWeight: 900
      }}>
        {props.cta}
      </div>
    </div>
  );
}
