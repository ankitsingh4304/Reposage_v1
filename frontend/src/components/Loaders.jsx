export function Ring({ size = 44 }) {
  return <span className="ring" style={{ width: size, height: size }} />;
}

export function Dots() {
  return (
    <span className="dots">
      <span />
      <span />
      <span />
    </span>
  );
}
