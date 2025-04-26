import L from "leaflet";
import { grayscaleTileLayer } from "./leaflet_grayscale";

// TODO update attribution
export const grayscaleLayer = grayscaleTileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  {
    attribution:
      "Tiles &copy; Esri &mdash; Esri, Maxar, Earthstar Geographics, and the GIS User Community",
  }
);
const colorLayer = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  {
    attribution:
      "Tiles &copy; Esri &mdash; Esri, Maxar, Earthstar Geographics, and the GIS User Community",
  }
);
const osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "© OpenStreetMap",
});
const osmHOT = L.tileLayer(
  "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
  {
    maxZoom: 19,
    attribution:
      "© OpenStreetMap contributors, Tiles style by Humanitarian OpenStreetMap Team hosted by OpenStreetMap France",
  }
);

export type BaseMapTypes =
  | "Colour"
  | "Greyscale"
  | "OpenStreetMap"
  | "OpenStreetMap.HOT";

export const BaseMaps: Record<BaseMapTypes, L.TileLayer> = {
  Colour: colorLayer,
  Greyscale: grayscaleLayer,
  OpenStreetMap: osm,
  "OpenStreetMap.HOT": osmHOT,
} as const;
