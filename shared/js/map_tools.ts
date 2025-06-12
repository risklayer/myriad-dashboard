import chroma from "chroma-js";
import L, { Layer } from "leaflet";
import "leaflet-defaulticon-compatibility";

import "leaflet-contour";
import "leaflet.control.opacity/src/L.Control.Opacity";
import {
  max,
  memoize,
  min,
  pick,
  range,
  sortedUniq,
  uniq,
  unzip,
} from "lodash";
import { BaseMaps, BaseMapTypes, grayscaleLayer } from "./base_map_layers";
import { activateButton, deactivateButton } from "./dom_tools";
import { floatTo3Digits } from "./utils";

// Using regular import fails to import proj4 properly.
import "../../node_modules/georaster-layer-for-leaflet/dist/v3/webpack/bundle/georaster-layer-for-leaflet.min.js";

export type ZoomToFitOption = "event" | "column" | "regions" | "auto" | false;
export type FormUpdateOptions = { zoomToFit?: ZoomToFitOption };
export type QuantisationType =
  | "logarithmic"
  | "equidistant"
  | "quantile"
  | "k-means";

export function handleMapButtonClick(
  clickedElement: HTMLInputElement | HTMLSelectElement | undefined,
  options: FormUpdateOptions | undefined,
  formId: string = "filters-form",
  fieldName: string = "column"
) {
  const filtersForm = document.getElementById(formId) as HTMLFormElement;
  const hiddenSelectionField = filtersForm[fieldName] as HTMLInputElement;
  if (
    clickedElement?.tagName === "BUTTON" &&
    clickedElement.classList.contains("show-on-map-button")
  ) {
    const value = clickedElement.value;
    if (hiddenSelectionField.value === value) {
      hiddenSelectionField.value = "";
      deactivateButton(clickedElement);
      options = { ...options, zoomToFit: false };
    } else {
      hiddenSelectionField.value = value;
      activateButton(clickedElement);
      // options = { ...options, zoomToFit: mapButtonZoomType };
    }
  }
  return options;
}
// class SVGIcon extends L.Icon {
//   createIcon(oldIcon?: HTMLElement) {
//     const icon = super.createIcon(oldIcon);
//     console.log(oldIcon, icon);
//     return oldIcon!;
//   }
// }
export function createIconSvg(
  type: string,
  size: number = 12,
  color = "currentColor"
) {
  return `<svg width="${size}"
                height="${size}"
                fill="${color}">
              <use xlink:href="/static/bootstrap-icons/bootstrap-icons.svg#${type}" />
            </svg>`;
}

export function getHazardMarker(
  hazardEvent: FilteredEventData & Record<string, number>,
  colors: chroma.Scale<chroma.Color>,
  colorBy: string
) {
  if (hazardEvent.hazard in hazardIconSettings) {
    return L.marker([hazardEvent.latitude, hazardEvent.longitude], {
      icon: getIcon(colors, hazardEvent, colorBy),
    });
  }
  warnIconMissing(hazardEvent.hazard);
  return L.circleMarker([hazardEvent.latitude, hazardEvent.longitude], {
    radius: 5,
    weight: 1,
    color: "#333333",
    fillColor: colors(hazardEvent[colorBy ?? 0]).toString(),
    opacity: 1,
    fillOpacity: 0.8,
  });
}
export const warnIconMissing = memoize((hazard: string) =>
  console.warn(`No icon configured for hazard: ${hazard}`)
);
export const hazardIconSettings: Record<
  string,
  { icon: string } & Partial<L.DivIconOptions>
> = {
  tornado: {
    icon: "tornado",
    iconAnchor: L.point(10, 16),
  },
  wind: {
    icon: "wind",
  },
  flood: {
    icon: "water",
  },
  winterstorm: {
    icon: "cloud-snow",
    iconAnchor: L.point(10, 16),
  },
  hurricane: {
    icon: "hurricane",
  },
  storm_surge: {
    icon: "tsunami",
    iconAnchor: L.point(10, 16),
  },
  drought: {
    icon: "sun",
    iconAnchor: L.point(10, 16),
  },
  wildfire: {
    icon: "fire",
    iconAnchor: L.point(10, 16),
  },
  earthquake: {
    icon: "soundwave",
  },
  eq: {
    icon: "soundwave",
  },
  heat_wave: {
    icon: "thermometer-sun",
  },
  // tropical-storm, cloud-lightning-rain, cloud-lightning-rain-fill,
};
const contrastingColor = memoize((color) => {
  const w = chroma.contrast("#ffffff", color);
  const b = chroma.contrast("#000000", color);
  return w > b ? "#ffffff" : "#000000";
});

export function getIcon(
  colors: chroma.Scale<chroma.Color>,
  event: FilteredEventData &
    Record<string, number> & { hazard: keyof typeof hazardIconSettings },
  colorBy: string
): L.Icon<L.IconOptions> | L.DivIcon | undefined {
  const { icon, ...settings } = hazardIconSettings[event.hazard]!;
  const color = colors(event[colorBy ?? 0]).toString();
  // hazardIconSettings[sample(Object.keys(hazardIconSettings))];
  return L.divIcon({
    html: `<div class="rounded-5 p-1 py-0 w-100 h-100" style="background:${color}">${createIconSvg(
      icon,
      12,
      contrastingColor(color)
    )}</div>`,
    className: "background-transparent",
    iconSize: L.point(20, 20),
    ...settings,
  });
}
export type FilteredEventData = {
  latitude: number;
  longitude: number;
  id: number;
  hazard: string;
};

document.body.addEventListener("htmx:confirm", function (evt) {
  const element = evt.target as HTMLElement;
  if (
    element.classList.contains("show-on-map-button") &&
    !element.classList.contains("active")
  ) {
    evt.preventDefault();
    const target = element.getAttribute("hx-target");
    if (target) {
      const targetElement = document.querySelector(target) as HTMLElement;
      if (targetElement) {
        targetElement.innerHTML = "";
      }
    }
    return;
  }
});

export enum LayerNames {
  Region = "region_layer",
  Heat = "heat_layer",
  FilteredItems = "filtered_items_layer",
  EventFootprint = "event_footprint_layer",
  SearchLocation = "search_location_layer",
  GeoRaster = "geo_raster",
}

export function createMap<TLayers extends LayerNames[]>({
  initialBaselayer,
  latitude,
  longitude,
  itemFieldName,
  tableSelectElementId,
  tableSelectButtonClass,
  layers,
}: {
  initialBaselayer: BaseMapTypes;
  latitude: number;
  longitude: number;
  itemFieldName: "event" | "column";
  tableSelectElementId: string;
  tableSelectButtonClass: string;
  layers: Record<TLayers[0], string>;
}) {
  const main_map: L.Map = L.map("map", {
    center: [latitude, longitude],
    zoom: 4, //recommended for a global view which is not too far zoomed out
    zoomControl: false, //deactivate zoom control at its default position
    layers: [BaseMaps[initialBaselayer] ?? grayscaleLayer],
  });

  /* Map controls */

  L.control
    .zoom({
      position: "topright",
    })
    .addTo(main_map);

  L.control
    .scale({
      position: "topleft",
      imperial: false,
    })
    .addTo(main_map);

  const LAYERS: Record<TLayers[0], L.Layer> = pick(
    {
      region_layer: createRegionLayer().addTo(main_map) as L.GeoJSON,
      heat_layer: createHeatLayer(main_map).addTo(main_map),
      filtered_items_layer: createFilteredEventsLayer().addTo(main_map),
      event_footprint_layer: createEventFootprintLayer().addTo(main_map),
      search_location_layer: createSearchLocationLayer().addTo(main_map),
      geo_raster: null as unknown as L.GridLayer,
    },
    Object.keys(layers)
  );

  const LEGENDS: Partial<Record<LayerNames, any>> = pick(
    {
      region_layer: null,
      heat_layer: null,
      filtered_items_layer: null,
      event_footprint_layer: null,
      search_location_layer: null,
      geo_raster: null,
    },
    Object.keys(layers)
  );

  const baseLayerControl = L.control
    .layers(
      BaseMaps,
      Object.entries(layers).reduce(
        (acc, [name, title]) =>
          LAYERS[name as LayerNames]
            ? {
                ...acc,
                [title]: LAYERS[name as LayerNames],
              }
            : acc,
        {}
      ),
      {
        position: "topleft",
        sortLayers: true,
      }
    )
    .addTo(main_map);

  // if (LayerNames.Heat in layers) {
  // const opacityControl = L.control
  //   .opacity(
  //     Object.entries(layers).reduce(
  //       (acc, [name, title]) =>
  //         LAYERS[name as LayerNames]
  //           ? {
  //               ...acc,
  //               [title]: LAYERS[name as LayerNames],
  //             }
  //           : acc,
  //       {}
  //     ),
  //     {
  //       position: "topleft",
  //       label: "Opacity",
  //       // collapsed: true,
  //     }
  //   )
  //   .addTo(main_map);
  // }

  // See https://github.com/ptma/Leaflet.Legend
  // No types available
  // @ts-ignore
  const mainLegend = new L.Control.Legend({
    position: "bottomleft",
    inactive: true,
    legends: [],
  });

  // @ts-ignore
  // const rightLegend = new L.Control.Legend({
  //   position: "bottomright",
  //   inactive: true,
  //   legends: [],
  // });

  // const topLegend = new L.Control.Legend({
  //   position: "topright",
  //   inactive: true,
  //   legends: [],
  // });

  /**
   * Background option is stored in URL state.
   * Leaflet allows modifying the base layer using an inbuilt Control but not with
   * external API, so instead we'll do it manually by setting the appropriate
   * radio input and letting leaflet do the rest.
   */
  function updateBaseLayer() {
    const settingsForm = document.getElementById(
      "settings-form"
    ) as HTMLFormElement;
    const baseLayer = settingsForm.base_layer.value;

    if (!baseLayer) {
      return;
    }
    // @ts-ignore
    const { _layerControlInputs: inputs } = baseLayerControl;
    for (const radio of inputs as HTMLInputElement[]) {
      const span = radio.nextElementSibling as HTMLSpanElement;
      // The label span has leading space
      if (span.innerText.trim() === baseLayer) {
        if (!radio.checked) {
          radio.checked = true;
          // Force leaflet to apply the new background
          radio.dispatchEvent(new Event("click"));
        }
        break;
      }
    }
  }

  function hideLegend(layer?: LayerNames) {
    if (layer) {
      if (LEGENDS[layer]) {
        main_map!.removeControl(LEGENDS[layer]);
      }
    }
    main_map!.removeControl(mainLegend);
  }

  function showLegend({
    layer,
    position = "bottomleft",
    paletteName,
    quantisation = "logarithmic",
    values = [],
    invertColors = false,
    title = null,
  }: {
    layer?: LayerNames;
    position?: "bottomleft" | "bottomright" | "topleft" | "topright";
    paletteName: chroma.BrewerPaletteName;
    invertColors: boolean;
    quantisation?: QuantisationType;
    values: number[];
    title?: string | null;
    layers?: L.Layer[];
  }): {
    values: number[];
    limits: number[];
    max: number;
    colors: chroma.Scale<chroma.Color>;
  } {
    const legend = layer
      ? (LEGENDS[layer] ??
        new L.Control.Legend({
          position: "bottomleft",
          inactive: true,
          legends: [],
        }))
      : mainLegend;

    if (layer) {
      LEGENDS[layer] = legend;
    }

    main_map.removeControl(legend);
    let max;
    let limits;
    let colors;
    ({ max, limits, colors, values } = calculateColors({
      values,
      paletteName,
      invertColors,
      quantisation,
    }));
    if (max) {
      const legendOptions = {
        ...legend.options,
        title,
        position,
        legends: limits
          .map((q, i) => {
            if (i === limits.length - 1) {
              return null;
            }
            const color = colors(q);
            const range = `${floatTo3Digits(limits[i]!)} – ${floatTo3Digits(limits[i + 1]!)}`;
            return {
              label: range,
              type: "polygon",
              sides: 4,
              color,
              fill: color,
            };
          })
          .filter(Boolean),
      };
      legend.initialize(legendOptions);
      main_map.addControl(legend);
    }
    return { colors, max, limits, values };
  }

  /**
   * Remove contents from a layer
   */
  function cleanupLayer(key: LayerNames) {
    if (LAYERS[key]) {
      if (key === LayerNames.GeoRaster) {
        if (LAYERS[key]) {
          baseLayerControl.removeLayer(LAYERS[LayerNames.GeoRaster]!);
          LAYERS[key].removeFrom(main_map);
          // @ts-ignore
          LAYERS[key] = null;
        }
      } else {
        LAYERS[key]!.clearLayers();
      }
    }
    if (LEGENDS[key]) {
      hideLegend(key);
    }
  }

  async function setGeoRasterLayer(
    {
      tiffString,
      paletteName,
      invertColors,
      quantisation,
      legendTitle,
      layerTitle,
    }: {
      tiffString: string;
      paletteName: chroma.BrewerPaletteName;
      invertColors: boolean;
      quantisation: QuantisationType;
      legendTitle: string;
      layerTitle: string;
    },
    geoRasterOptions = {}
  ) {
    // https://github.com/GeoTIFF/georaster-layer-for-leaflet

    // Tiff content is returned as part of the data in BASE64 format. Convert to
    // ASCII, then put in an array buffer to parse to geotiff library for
    // parsing. (It also supports Blob, but only if the projection metadata is
    // in the file, see https://github.com/GeoTIFF/georaster/issues/83).
    const tiffArray = Uint8Array.from(atob(tiffString), (c) => c.charCodeAt(0));
    const buffer = new ArrayBuffer(tiffArray.length);
    const view = new Uint8Array(buffer);
    view.set(tiffArray);
    const georaster = await window.parseGeoraster(
      buffer,
      { projection: 4326 },
      true
    );

    // console.log("georaster:", georaster);

    const values = georaster.values
      .flat()
      .map((v) => Array.from(v))
      .flat();

    const { colors, max } = showLegend({
      layer: LayerNames.GeoRaster,
      position: "bottomright",
      values,
      paletteName,
      invertColors,
      quantisation,
      title: legendTitle,
    });

    const colorCutoff = max / 160;

    /*
    https://leafletjs.com/reference.html#gridlayer
    */
    LAYERS[LayerNames.GeoRaster] = new window.GeoRasterLayer({
      georaster,
      opacity: 0.7,
      pixelValuesToColorFn: (val: number) =>
        val > colorCutoff ? colors(val) : null,
      pane: "overlayPane",
      ...geoRasterOptions,
    }).addTo(main_map);

    baseLayerControl.addOverlay(LAYERS[LayerNames.GeoRaster]!, layerTitle);
  }

  /**
   * Pan back to the initial starting point
   */
  function returnHome() {
    main_map.flyTo(new L.LatLng(latitude, longitude), 4, {
      animate: false,
    });
  }

  function zoomTo(layer: L.FeatureGroup | null, options: L.FitBoundsOptions) {
    const bounds = layer?.getBounds();
    if (bounds?.isValid()) {
      main_map.invalidateSize().fitBounds(bounds, options);
    }
  }

  function updateMapButtonStates() {
    const filtersForm = document.getElementById(
      "filters-form"
    ) as HTMLFormElement;
    const item = (filtersForm[itemFieldName] as HTMLInputElement)?.value;
    (
      document.querySelectorAll(
        ".show-on-map-button"
      ) as NodeListOf<HTMLButtonElement>
    ).forEach((button: HTMLButtonElement) => {
      if (button.value === item) {
        activateButton(button);
      } else {
        deactivateButton(button);
      }
    });
  }

  function updateTableButtonStates() {
    const tableColumnsSelect = document.getElementById(
      tableSelectElementId
    ) as HTMLSelectElement;
    const keys = new Set(
      Array.from(tableColumnsSelect.options).map((option) => option.value)
    );
    (
      document.querySelectorAll(
        `.${tableSelectButtonClass}[data-bs-toggle='button']`
      ) as NodeListOf<HTMLButtonElement>
    ).forEach((button: HTMLButtonElement) => {
      if (keys.has(button.value)) {
        activateButton(button);
      } else {
        deactivateButton(button);
      }
    });
  }

  window.zoomToRegions = function zoomToRegions() {
    if (LAYERS.region_layer.getLayers().length) {
      zoomTo(LAYERS.region_layer, {
        padding: [1, 1],
        maxZoom: 11,
      });
    } else {
      returnHome();
    }
  };

  window.zoomToEvent = function zoomToRegions() {
    zoomTo(LAYERS.event_footprint_layer, {
      padding: [10, 10],
      maxZoom: 11,
    });
  };

  window.zoomToAllEvents = function zoomToAllEvents() {
    zoomTo(LAYERS.filtered_items_layer, {
      padding: [10, 10],
      maxZoom: 11,
    });
  };

  main_map.on("overlayadd", function (eventLayer) {
    for (const key of Object.keys(layers)) {
      if (
        eventLayer.layer === LAYERS[key as LayerNames] &&
        LEGENDS[key as LayerNames]
      ) {
        if (LEGENDS[key as LayerNames].options.legends.length) {
          main_map.addControl(LEGENDS[key as LayerNames]);
        }
        break;
      }
    }
  });

  main_map.on("overlayremove", function (eventLayer) {
    for (const key of Object.keys(layers)) {
      if (
        eventLayer.layer === LAYERS[key as LayerNames] &&
        LEGENDS[key as LayerNames]
      ) {
        main_map.removeControl(LEGENDS[key as LayerNames]);
        break;
      }
    }
  });

  return {
    main_map,
    LAYERS,
    hideLegend,
    showLegend,
    cleanupLayer,
    updateBaseLayer,
    returnHome,
    zoomTo,
    updateMapButtonStates,
    updateTableButtonStates,
    setGeoRasterLayer,
  };
}

export function calculateColors({
  values,
  paletteName,
  invertColors,
  quantisation,
}: {
  values: number[];
  paletteName: chroma.BrewerPaletteName;
  invertColors: boolean;
  quantisation: QuantisationType;
}) {
  values = values.filter(Boolean);
  const colorsList = [...chroma.brewer[paletteName]].reverse();
  if (invertColors === (colorsList.length === 11)) {
    colorsList.reverse();
  }
  const colorScale = chroma.scale(colorsList);
  const max = values?.length ? Math.max(...values) : 0;
  const count = chroma.brewer[paletteName].length;
  const limits = chroma.limits(
    values,
    quantisation as "e" | "q" | "l" | "k",
    count
  );
  const colors = colorScale.domain(limits);
  return { max, limits, colors, values };
}

function createRegionLayer() {
  return L.geoJSON([], {
    interactive: false,
    style: { weight: 1 },
  });
}

function createEventFootprintLayer() {
  return L.geoJSON([], {
    interactive: true,
    style: (feature) => {
      if (!feature) {
        return {};
      }
      const color = "magenta";
      const fillColor = "magenta";
      return { color, fillColor, weight: 3, fillOpacity: 0.7 };
    },
  });
}

function createSearchLocationLayer(): L.FeatureGroup<any> {
  return L.featureGroup();
}

function createFilteredEventsLayer(): L.FeatureGroup<FilteredEventData> {
  return L.featureGroup();
}

function createHeatLayer(map: L.Map): L.Layer {
  // https://github.com/JamesRunnalls/leaflet-contour?tab=readme-ov-file#api-reference
  // @ts-ignore
  const pane = map.createPane("heatPane");

  pane.style.opacity = "1";

  // @ts-ignore
  return new L.HeatLayer(null, {
    pane: "heatPane",
    thresholds: 10,
    opacity: 0.5,
  }) as unknown as L.Layer;
}

/**
 * Takes an array of arrays with longitude, latitude and value, converts
 * them into an object with a grid of x, y and z arrays of arrays, padded with
 * null values on all sides for compatibility with leaflet-contour.
 * @param data An array of [longitude, latitude, value] tuples
 * @returns An object with x, y and z arrays
 */
export function footprintToCartesian(
  data: [longitude: number, latitude: number, value: number][]
): {
  x: number[][];
  y: number[][];
  z: (number | null)[][];
} {
  const [xAll, yAll, _] = unzip(data);
  const minX = min(xAll)!;
  const maxX = max(xAll)!;
  const minY = min(yAll)!;
  const maxY = max(yAll)!;
  const deltaX = min(
    sortedUniq(uniq(xAll))
      .map((val, i, obj) => (i ? Math.abs(val - obj[i - 1]!) : null))
      .filter(Boolean)
  ) as number;
  const deltaY = min(
    sortedUniq(uniq(yAll))
      .map((val, i, obj) => (i ? Math.abs(val - obj[i - 1]!) : null))
      .filter(Boolean)
  ) as number;
  // One for each value, plus 1 for the end value, plus buffer tiles on each size
  const ySize = (Math.ceil(maxY) - Math.floor(minY)) / deltaY + 3;
  const xRow = range(
    Math.floor(minX - deltaX),
    Math.ceil(maxX + 3 * deltaX),
    deltaX
  );
  const xSize = xRow.length;
  const x = Array(ySize).fill(xRow);
  const y = Array(ySize)
    .fill(null)
    .map((_, i) => maxY - (i - 1) * deltaY)
    .map((val) => Array(xSize).fill(val));
  const z = Array(ySize)
    .fill(null)
    .map(() => Array(xSize).fill(null));
  const xMap = new Map<number, number>();
  x[0].forEach((val: number, i: number) => xMap.set(val, i));
  const yMap = new Map<number, number>();
  y.forEach((val: number[], i: number) => yMap.set(val[0]!, i));

  data.forEach(
    ([xVal, yVal, zVal]) => (z[yMap.get(yVal)!]![xMap.get(xVal)!] = zVal)
  );

  return {
    x,
    y,
    z,
  };
}

// Fix limitation of leaflet.control.opacity that restricts it
// to layers with a url
L.Control.Opacity.include({
  _addItem: function (obj) {
    const label = document.createElement("label");
    let input = document.createElement("input");
    if (obj.overlay) {
      input.type = "range";
      input.className = "leaflet-control-layers-range";
      input.min = "0";
      input.max = "100";
      input.value = `${obj.layer.options.opacity * 100}`;
    } else {
      input = this._createRadioElement("leaflet-base-layers");
    }
    this._layerControlInputs.push(input);
    input.layerId = L.Util.stamp(obj.layer);
    input.addEventListener("input", (event) => {
      const rgValue = (event.target as HTMLInputElement)
        .value as unknown as number;
      const layer = this._getLayer(input.layerId).layer;
      if (layer.setOpacity) {
        layer.setOpacity(Number(rgValue / 100));
      } else {
        (obj.layer.getPane() as HTMLDivElement).style.opacity = Number(
          rgValue / 100
        );
      }
    });
    const name = document.createElement("span");
    name.innerHTML = " " + obj.name;
    const holder = document.createElement("div");
    const holder2 = document.createElement("div");
    label.appendChild(holder);
    holder.appendChild(name);
    label.appendChild(holder2);
    holder2.appendChild(input);
    const container = obj.overlay ? this._overlaysList : this._baseLayersList;
    container.appendChild(label);
  },
});

L.HeatLayer = L.Contour.extend({
  options: {
    thresholds: 50,
    color: 1,
    pane: "heatPane",
  },
});
