// Lectify icon set: hand-drawn on a 24px grid, stroke-first "fountain pen /
// notebook" family. Round joins, slightly uneven terminals, an ink-dot accent
// where it helps. Replaces @phosphor-icons/react and lucide-react; exported
// names match what the code already imported so call sites stay unchanged.
import { forwardRef } from "react";

const WEIGHT = { thin: 1.25, light: 1.5, bold: 2.25 };

export const Icon = forwardRef(function Icon(
  { size = 24, title, weight, mirrored, color, strokeWidth, children, style, ...rest },
  ref,
) {
  // Phosphor-style props: weight="fill" fills closed shapes, bold/light tune the
  // stroke, anything else (e.g. the two-tone weight) falls back to regular.
  const filled = weight === "fill";
  const labelled = title != null || rest["aria-label"] != null;
  return (
    <svg
      ref={ref}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill={filled ? "currentColor" : "none"}
      stroke={color || "currentColor"}
      strokeWidth={strokeWidth ?? WEIGHT[weight] ?? 1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
      aria-hidden={labelled ? undefined : true}
      role={labelled ? "img" : undefined}
      style={mirrored ? { transform: "scaleX(-1)", ...style } : style}
      {...rest}
    >
      {title != null && <title>{title}</title>}
      {typeof children === "function" ? children(filled) : children}
    </svg>
  );
});

function make(name, body) {
  const C = forwardRef((props, ref) => (
    <Icon ref={ref} {...props}>
      {body}
    </Icon>
  ));
  C.displayName = name;
  return C;
}

// Ink dot: the family's signature accent.
const Dot = ({ x, y, r = 1 }) => <circle cx={x} cy={y} r={r} fill="currentColor" stroke="none" />;

/* ---- writing & study ---- */
export const PenNib = make(
  "PenNib",
  <>
    <path d="M4.5 19.5l3.6-8.4 5.6-5.6 4.8 4.8-5.6 5.6z" />
    <path d="M4.5 19.5l5.2-5.2" />
    <circle cx="10.9" cy="13.1" r="1.2" />
    <path d="M15.6 3.5l4.9 4.9" />
    <Dot x={3.1} y={21.1} r={0.9} />
  </>,
);
export const Pencil = make(
  "Pencil",
  <>
    <path d="M4 20l1-4.6L15.6 4.8c.8-.8 2-.8 2.8 0l.8.8c.8.8.8 2 0 2.8L8.6 19z" />
    <path d="M13.8 6.6l3.6 3.6" />
    <path d="M5 15.4l3.6 3.6" />
  </>,
);
export const PencilSimple = make(
  "PencilSimple",
  <>
    <path d="M4 20l1-4.6L15.6 4.8c.8-.8 2-.8 2.8 0l.8.8c.8.8.8 2 0 2.8L8.6 19z" />
    <path d="M13.8 6.6l3.6 3.6" />
  </>,
);
export const BookOpen = make(
  "BookOpen",
  <>
    <path d="M12 6.5C10.2 5 7.6 4.4 3.5 4.6v13.6c4.1-.2 6.7.4 8.5 1.9 1.8-1.5 4.4-2.1 8.5-1.9V4.6C16.4 4.4 13.8 5 12 6.5z" />
    <path d="M12 6.5v13.4" />
  </>,
);
export const BookBookmark = make(
  "BookBookmark",
  <>
    <path d="M5 19.6V5.6c0-1.2.9-2.1 2.1-2.1H19v14.2H7.1C5.9 17.7 5 18.6 5 19.6s.9 1.9 2.1 1.9H19" />
    <path d="M10.5 3.5v6.5l2.2-1.6 2.3 1.6V3.5" />
  </>,
);
export const BookmarkSimple = make(
  "BookmarkSimple",
  <path d="M6.5 4.8c0-.7.6-1.3 1.3-1.3h8.4c.7 0 1.3.6 1.3 1.3v15.7L12 16.8l-5.5 3.7z" />,
);
export const GraduationCap = make(
  "GraduationCap",
  <>
    <path d="M2.5 9.3L12 5l9.5 4.3-9.5 4.3z" />
    <path d="M6.5 11.2v4.6c1.6 1.6 3.4 2.4 5.5 2.4s3.9-.8 5.5-2.4v-4.6" />
    <path d="M21.5 9.3v5" />
    <Dot x={21.5} y={16.2} />
  </>,
);
export const ChalkboardTeacher = make(
  "ChalkboardTeacher",
  <>
    <path d="M3.5 13V5.6c0-.9.7-1.6 1.6-1.6h13.8c.9 0 1.6.7 1.6 1.6v10.8c0 .9-.7 1.6-1.6 1.6h-4" />
    <circle cx="8.5" cy="11" r="2.5" />
    <path d="M3.5 20.5c.8-2.2 2.7-3.5 5-3.5s4.2 1.3 5 3.5" />
    <path d="M12.5 13l4-3.5" />
  </>,
);
export const Brain = make(
  "Brain",
  <>
    <path d="M12 5.5c-.8-1.4-2.2-2-3.6-1.8-1.7.3-2.9 1.7-2.9 3.4-1.6.5-2.5 2-2.3 3.6.1 1 .6 1.8 1.4 2.4-.6.9-.7 2.1-.2 3.1.6 1.2 1.9 1.9 3.2 1.8.4 1.5 1.8 2.5 3.4 2.4.4 0 .7-.1 1-.3" />
    <path d="M12 5.5c.8-1.4 2.2-2 3.6-1.8 1.7.3 2.9 1.7 2.9 3.4 1.6.5 2.5 2 2.3 3.6-.1 1-.6 1.8-1.4 2.4.6.9.7 2.1.2 3.1-.6 1.2-1.9 1.9-3.2 1.8-.4 1.5-1.8 2.5-3.4 2.4-.4 0-.7-.1-1-.3" />
    <path d="M12 5.5v14.6" />
    <path d="M8.3 9.4c1 .2 1.8.9 2 1.9" />
    <path d="M15.7 13.6c-1-.2-1.8-.9-2-1.9" />
  </>,
);
export const Translate = make(
  "Translate",
  <>
    <path d="M3.5 5.5h9" />
    <path d="M8 3.5v2" />
    <path d="M10.8 5.5c-.9 3.6-3.4 6.4-6.6 7.8" />
    <path d="M6 8.4c1.1 1.9 2.8 3.4 4.8 4.4" />
    <path d="M12.5 20.5l3.8-9 3.8 9" />
    <path d="M13.8 17.5h5" />
  </>,
);
export const FileAudio = make(
  "FileAudio",
  <>
    <path d="M14 3.5H6.8c-.9 0-1.6.7-1.6 1.6v13.8c0 .9.7 1.6 1.6 1.6h10.4c.9 0 1.6-.7 1.6-1.6V8.3z" />
    <path d="M14 3.5v4.8h4.8" />
    <path d="M8.8 13.6v2.3M11.2 11.6v6.3M13.6 12.8v3.9M16 14v1.5" />
  </>,
);
export const CalendarBlank = make(
  "CalendarBlank",
  <>
    <rect x="3.8" y="5" width="16.4" height="15.5" rx="2" />
    <path d="M3.8 9.8h16.4" />
    <path d="M8 3v4M16 3v4" />
    <Dot x={8.2} y={14.2} />
  </>,
);

/* ---- voice & media ---- */
export const Microphone = make(
  "Microphone",
  <>
    <rect x="9" y="3" width="6" height="11" rx="3" />
    <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0" />
    <path d="M12 18v3" />
    <path d="M8.8 21h6.6" />
    <Dot x={19.8} y={5.2} r={0.9} />
  </>,
);
export const Play = make(
  "Play",
  <path d="M6.8 4.8v14.4c0 .8.9 1.3 1.6.9l11-7.2c.6-.4.6-1.3 0-1.7l-11-7.2c-.7-.4-1.6.1-1.6.8z" />,
);
export const Pause = make(
  "Pause",
  <>
    <rect x="6.2" y="4.5" width="3.8" height="15" rx="1.2" />
    <rect x="14" y="4.5" width="3.8" height="15" rx="1.2" />
  </>,
);

/* ---- marks & accents ---- */
export const Sparkle = make(
  "Sparkle",
  <>
    <path d="M11 3.5c.7 4.2 2.8 6.3 7 7-4.2.7-6.3 2.8-7 7-.7-4.2-2.8-6.3-7-7 4.2-.7 6.3-2.8 7-7z" />
    <Dot x={19} y={19} r={1.1} />
  </>,
);
export const Lightning = make("Lightning", <path d="M13.5 2.8L5.2 13.4h6l-1.1 7.8 8.7-10.9h-6.1z" />);
export const ChartLine = make(
  "ChartLine",
  <>
    <path d="M3.5 3.8v16.7h17" />
    <path d="M7 15.5l3.6-4.4 3.2 2.6 5.2-6.4" />
    <Dot x={19.4} y={6.9} r={1.1} />
  </>,
);
export const Sun = make(
  "Sun",
  <>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2.8v2M12 19.2v2M2.8 12h2M19.2 12h2M5.5 5.5l1.4 1.4M17.1 17.1l1.4 1.4M5.5 18.5l1.4-1.4M17.1 6.9l1.4-1.4" />
  </>,
);
export const MoonStars = make(
  "MoonStars",
  <>
    <path d="M19.5 14.6A7.9 7.9 0 0 1 9.4 4.5a7.9 7.9 0 1 0 10.1 10.1z" />
    <path d="M16.5 3.5v3M15 5h3" />
    <Dot x={20.2} y={9} r={0.9} />
  </>,
);
export const Warning = make(
  "Warning",
  <>
    <path d="M10.6 4.3L3 17.6c-.6 1.1.2 2.4 1.4 2.4h15.2c1.2 0 2-1.3 1.4-2.4L13.4 4.3c-.6-1.1-2.2-1.1-2.8 0z" />
    <path d="M12 9.5v4.2" />
    <Dot x={12} y={16.8} r={1.05} />
  </>,
);
export const WarningCircle = make(
  "WarningCircle",
  <>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.8v4.8" />
    <Dot x={12} y={16} r={1.05} />
  </>,
);
export const HourglassMedium = make(
  "HourglassMedium",
  <>
    <path d="M6.5 3.5h11M6.5 20.5h11" />
    <path d="M7.5 3.5c0 4.5 4.5 5.5 4.5 8.5s-4.5 4-4.5 8.5" />
    <path d="M16.5 3.5c0 4.5-4.5 5.5-4.5 8.5s4.5 4 4.5 8.5" />
    <path d="M9.6 17.8c1.3-.9 3.5-.9 4.8 0" />
    <Dot x={12} y={14.8} r={0.8} />
  </>,
);

/* ---- confirm / dismiss ---- */
export const Check = make("Check", <path d="M4.5 12.8l4.6 4.4L19.5 6.5" />);
export const CheckCircle = make("CheckCircle", (filled) => (
  <>
    <circle cx="12" cy="12" r="8.5" />
    <path
      d="M8.2 12.3l2.7 2.6 5-5.4"
      fill="none"
      stroke={filled ? "hsl(var(--paper, 0 0% 100%))" : undefined}
    />
  </>
));
export const X = make("X", <path d="M6 6.2l11.8 11.6M17.8 6L6.2 17.8" />);
export const Plus = make("Plus", <path d="M12 4.8v14.4M4.8 12h14.4" />);
export const Minus = make("Minus", <path d="M4.8 12h14.4" />);
export const Circle = make("Circle", <circle cx="12" cy="12" r="8.5" />);

/* ---- direction ---- */
export const ChevronDown = make("ChevronDown", <path d="M6 9.2l6 5.8 6-5.8" />);
export const ChevronUp = make("ChevronUp", <path d="M6 14.8l6-5.8 6 5.8" />);
export const ChevronRight = make("ChevronRight", <path d="M9.2 6l5.8 6-5.8 6" />);
export const ChevronLeft = make("ChevronLeft", <path d="M14.8 6L9 12l5.8 6" />);
export const CaretRight = ChevronRight;
export const CaretLeft = ChevronLeft;
export const ArrowLeft = make(
  "ArrowLeft",
  <path d="M19.5 12H5M10.5 6.2L4.8 12l5.7 5.8" />,
);
export const ArrowRight = make(
  "ArrowRight",
  <path d="M4.5 12H19M13.5 6.2l5.7 5.8-5.7 5.8" />,
);
export const ArrowClockwise = make(
  "ArrowClockwise",
  <>
    <path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3" />
    <path d="M19.6 3.8v4.4h-4.4" />
  </>,
);
export const ArrowsClockwise = make(
  "ArrowsClockwise",
  <>
    <path d="M4.5 10.5A7.5 7.5 0 0 1 18 7.5" />
    <path d="M18.6 3.6v4h-4" />
    <path d="M19.5 13.5A7.5 7.5 0 0 1 6 16.5" />
    <path d="M5.4 20.4v-4h4" />
  </>,
);
const tray = <path d="M4.5 15.5v3.2c0 .9.7 1.6 1.6 1.6h11.8c.9 0 1.6-.7 1.6-1.6v-3.2" />;
export const Download = make(
  "Download",
  <>
    <path d="M12 3.8v11M7.4 10.6L12 15l4.6-4.4" />
    {tray}
  </>,
);
export const DownloadSimple = Download;
export const UploadSimple = make(
  "UploadSimple",
  <>
    <path d="M12 15.2V4M7.4 8.4L12 3.8l4.6 4.6" />
    {tray}
  </>,
);
export const SignOut = make(
  "SignOut",
  <>
    <path d="M9.5 20.5H5.6c-.9 0-1.6-.7-1.6-1.6V5.1c0-.9.7-1.6 1.6-1.6h3.9" />
    <path d="M14.8 7.6l4.4 4.4-4.4 4.4M19 12H9.5" />
  </>,
);
export const PaperPlaneTilt = make(
  "PaperPlaneTilt",
  <>
    <path d="M20.5 3.5L3.5 10.2l6.8 3.1 3.2 7.2z" />
    <path d="M20.5 3.5l-10.2 9.8" />
  </>,
);

/* ---- people ---- */
export const User = make(
  "User",
  <>
    <circle cx="12" cy="8" r="4" />
    <path d="M4.5 20.5c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5" />
  </>,
);
export const Users = make(
  "Users",
  <>
    <circle cx="9" cy="8.5" r="3.5" />
    <path d="M2.8 19.5c.9-3.2 3.2-4.9 6.2-4.9s5.3 1.7 6.2 4.9" />
    <path d="M15.2 5.2a3.4 3.4 0 0 1 0 6.6M17.2 14.9c2 .6 3.4 2.1 4 4.6" />
  </>,
);
export const UsersThree = make(
  "UsersThree",
  <>
    <circle cx="12" cy="10" r="3" />
    <path d="M6.8 19.5c.9-2.6 2.8-4 5.2-4s4.3 1.4 5.2 4" />
    <circle cx="5.5" cy="8" r="2.2" />
    <circle cx="18.5" cy="8" r="2.2" />
    <path d="M2.5 15.5c.6-1.6 1.7-2.4 3.2-2.5M21.5 15.5c-.6-1.6-1.7-2.4-3.2-2.5" />
  </>,
);
export const Robot = make(
  "Robot",
  <>
    <rect x="5" y="8" width="14" height="11" rx="3" />
    <path d="M12 8V5" />
    <Dot x={12} y={3.8} r={1.1} />
    <Dot x={9.5} y={13} r={1.1} />
    <Dot x={14.5} y={13} r={1.1} />
    <path d="M10 16.2h4M3 12.5V15M21 12.5V15" />
  </>,
);
export const ChatCircle = make(
  "ChatCircle",
  <path d="M4.3 16.4A8.5 8.5 0 1 1 7.6 19.4L3.5 20.5z" />,
);

/* ---- places & structure ---- */
export const Buildings = make(
  "Buildings",
  <>
    <path d="M3.5 20.5h17" />
    <path d="M5.5 20.5V5.2c0-.9.7-1.7 1.7-1.7h5.6c.9 0 1.7.8 1.7 1.7v15.3" />
    <path d="M14.5 9.5h3.3c.9 0 1.7.8 1.7 1.7v9.3" />
    <path d="M8.5 7.5h2M8.5 11h2M8.5 14.5h2M16.5 13.5h1M16.5 16.5h1" />
  </>,
);
export const GitBranch = make(
  "GitBranch",
  <>
    <circle cx="6.5" cy="5.5" r="2" />
    <circle cx="6.5" cy="18.5" r="2" />
    <circle cx="17.5" cy="6.5" r="2" />
    <path d="M6.5 7.5v9M17.5 8.5c0 4.5-5 4.2-9.6 8.5" />
  </>,
);
export const QrCode = make(
  "QrCode",
  <>
    <rect x="3.5" y="3.5" width="6" height="6" rx="1" />
    <rect x="14.5" y="3.5" width="6" height="6" rx="1" />
    <rect x="3.5" y="14.5" width="6" height="6" rx="1" />
    <Dot x={6.5} y={6.5} r={0.9} />
    <Dot x={17.5} y={6.5} r={0.9} />
    <Dot x={6.5} y={17.5} r={0.9} />
    <path d="M14.5 14.5H17V17M20.5 14.5v.5M14.5 20.5h6M18.5 17.5h2" />
  </>,
);

/* ---- utility ---- */
export const Eye = make(
  "Eye",
  <>
    <path d="M2.8 12c2.2-4.2 5.3-6.3 9.2-6.3s7 2.1 9.2 6.3c-2.2 4.2-5.3 6.3-9.2 6.3S5 16.2 2.8 12z" />
    <circle cx="12" cy="12" r="3" />
    <Dot x={12.9} y={11.1} r={0.9} />
  </>,
);
export const EyeSlash = make(
  "EyeSlash",
  <>
    <path d="M2.8 12c2.2-4.2 5.3-6.3 9.2-6.3s7 2.1 9.2 6.3c-2.2 4.2-5.3 6.3-9.2 6.3S5 16.2 2.8 12z" />
    <circle cx="12" cy="12" r="3" />
    <path d="M4 3.5l16 17" />
  </>,
);
export const Search = make(
  "Search",
  <>
    <circle cx="10.5" cy="10.5" r="6.5" />
    <path d="M15.3 15.3l5.2 5.2" />
  </>,
);
const trashBody = (
  <>
    <path d="M4 6.5h16" />
    <path d="M9.5 6.5V4.8c0-.7.5-1.3 1.2-1.3h2.6c.7 0 1.2.6 1.2 1.3v1.7" />
    <path d="M6.2 6.5l.9 12.6c.1.8.7 1.4 1.5 1.4h6.8c.8 0 1.4-.6 1.5-1.4l.9-12.6" />
  </>
);
export const Trash = make(
  "Trash",
  <>
    {trashBody}
    <path d="M10 10.5v6M14 10.5v6" />
  </>,
);
export const TrashSimple = make("TrashSimple", trashBody);
export const GripVertical = make(
  "GripVertical",
  <>
    <Dot x={9} y={6} r={1.1} />
    <Dot x={15} y={6} r={1.1} />
    <Dot x={9} y={12} r={1.1} />
    <Dot x={15} y={12} r={1.1} />
    <Dot x={9} y={18} r={1.1} />
    <Dot x={15} y={18} r={1.1} />
  </>,
);
export const MoreHorizontal = make(
  "MoreHorizontal",
  <>
    <Dot x={6} y={12} r={1.3} />
    <Dot x={12} y={12} r={1.3} />
    <Dot x={18} y={12} r={1.3} />
  </>,
);

export default Icon;
