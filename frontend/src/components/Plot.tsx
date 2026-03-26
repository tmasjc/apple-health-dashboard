// react-plotly.js is CJS; handle default export interop
import reactPlotly from "react-plotly.js";

// Vite CJS interop may wrap the module — unwrap if needed
const Plot = (reactPlotly as any).default ?? reactPlotly;
export default Plot;
