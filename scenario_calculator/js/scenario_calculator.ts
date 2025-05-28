import DataTable, {
  ConfigColumns,
  Api as DataTableApi,
  Feature as DataTableFeature,
} from "datatables.net-bs5";
import "datatables.net-buttons-bs5/js/buttons.bootstrap5";
import "datatables.net-buttons/js/buttons.colVis";
import "datatables.net-buttons/js/buttons.html5";
import "datatables.net-buttons/js/buttons.print";
import "datatables.net-buttons/js/dataTables.buttons";
import jQuery from "jquery";

import type { Feature } from "geojson";

import chroma from "chroma-js";
import L, { FeatureGroup } from "leaflet";
import "../../shared/js/leaflet_grayscale";

import "@gnatih/leaflet.legend";

import { LayersControlEvent } from "leaflet";
import { keyBy, mapValues, pick, uniq } from "lodash";
import { toast } from "../../dashboard/js/scripts";
import {
  components,
  DataTableColumnSchema,
  FeatureCollectionSchema,
  HrscEventSchema,
  Nuts3AreaSchema,
  ShapeFeature,
  type CountriesEnum,
} from "../../data/types/api";
import { BaseMapTypes } from "../../shared/js/base_map_layers";
import {
  applyAllFormValuesToParams,
  applyParamsToAllForms,
  deactivateButton,
  getCountriesByAreaCode,
  getParamsGrouped,
  reorderSelectArrayValues,
  resetSelectTreeIndeterminate,
  toggleSelectArray,
} from "../../shared/js/dom_tools";
import {
  createMap,
  FilteredEventData,
  footprintToCartesian,
  FormUpdateOptions,
  getHazardMarker,
  handleMapButtonClick,
  LayerNames,
  QuantisationType,
} from "../../shared/js/map_tools";
import {
  createGeoJSONDownload,
  floatTo3Digits,
  slugify,
} from "../../shared/js/utils";
import { GeometryObject } from "../../static/@types/geojson";
import { Dictionary } from "../../static/@types/lodash";
import {
  downloadGeoJSON,
  getAreasMap,
  getCombinedImpact,
  getEventDetail,
  getShapesList,
} from "./scenario_calculator_api";
import { TableDatum } from "./types";

declare global {
  interface Window {}
}

const options = document.getElementById("scenario_calculator_script")!.dataset;
const INITIAL_LATITUDE = parseFloat(options.latitude ?? "0");
const INITIAL_LONGITUDE = parseFloat(options.longitude ?? "0");
const INITIAL_RADIUS = parseFloat(options.radius ?? "0");
const INITIAL_BASELAYER =
  ((document.getElementById("id_base_layer") as HTMLInputElement)
    .value as BaseMapTypes) || "Greyscale";

const INITIAL_PROBABILITY_LATITUDE = parseFloat(
  // @ts-ignore
  ((document.getElementById("id_p-latitude") as HTMLInputElement).value ||
    options.latitude) ??
    "0"
);
const INITIAL_PROBABILITY_LONGITUDE = parseFloat(
  // @ts-ignore
  ((document.getElementById("id_p-longitude") as HTMLInputElement).value ||
    options.longitude) ??
    "0"
);

const WINTERSTORM_MAXIMUM_RADIUS = parseFloat(
  options.winterstormRadius ?? "100"
);

const ALL_PAGE_FORMS = [
  "settings-form",
  "filters-form",
  "regions-form",
  "table-events-form",
  "probability-form-1",
  "probability-form-2",
  "probability-shared-form",
];

const {
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
} = createMap({
  initialBaselayer: INITIAL_BASELAYER,
  latitude: INITIAL_LATITUDE,
  longitude: INITIAL_LONGITUDE,
  itemFieldName: "event",
  tableSelectElementId: "table-events",
  tableSelectButtonClass: "table-column-button",
  layers: {
    [LayerNames.SearchLocation]: "Search location",
    [LayerNames.FilteredItems]: "Search results",
    [LayerNames.Heat]: "Regional event footprint",
    [LayerNames.EventFootprint]: "Polygon local event footprint",
    [LayerNames.GeoRaster]: "Raster local event",
    [LayerNames.Region]: "Combined results",
  },
});

// window.htmx.logAll();

const filter_circle = L.circle([INITIAL_LATITUDE, INITIAL_LONGITUDE], {
  radius: INITIAL_RADIUS * 1000,
  weight: 1,
  color: "#ffffff",
  fillColor: "#ffffff",
  opacity: 0.8,
  fillOpacity: 0.1,
}).addTo(LAYERS.search_location_layer);

const crosshair = L.marker(
  [INITIAL_PROBABILITY_LATITUDE, INITIAL_PROBABILITY_LONGITUDE],
  {
    // radius: INITIAL_RADIUS * 1000,
    // weight: 1,
    // color: "#ffffff",
    // fillColor: "#ffffff",
    // opacity: 0.8,
    // fillOpacity: 0.1,
  }
).addTo(LAYERS.search_location_layer);

let values_table: DataTableApi | null = null;

let choosingPoint = false;
window.choosePoint = function choosePoint(event: MouseEvent) {
  event.preventDefault();
  event.stopImmediatePropagation();
  choosingPoint = true;
  document.getElementById("map")!.style.cursor = "crosshair";
};

function stopChoosingPoint() {
  choosingPoint = false;
  document.getElementById("map")!.style.cursor = "";
  const button = document.getElementById("choose-point-button")!;
  deactivateButton(button);
}

main_map.addEventListener("click", (event: L.LeafletMouseEvent) => {
  if (choosingPoint) {
    const { latlng } = event;
    if (!latlng) {
      return;
    }
    const probabilitySharedForm = document.getElementById(
      "probability-shared-form"
    ) as HTMLFormElement;
    probabilitySharedForm["p-latitude"].value = latlng.lat;
    probabilitySharedForm["p-longitude"].value = latlng.lng;
    crosshair.setLatLng(latlng);
    document.getElementById("get-probability-button")?.click();
    window.updateParams();
  }
});

document.addEventListener("click", (event) => {
  if (
    event.target &&
    !(event.target as HTMLElement).closest("#map") &&
    (event.target as HTMLElement).id !== "get-probability-button"
  ) {
    stopChoosingPoint();
  }
});

window.addEventListener("blur", stopChoosingPoint);
window.addEventListener("keydown", (evt) => {
  if (evt.key === "Escape") {
    stopChoosingPoint();
  }
});

window.formUpdate = function formUpdate(
  clickedElement?: HTMLSelectElement | HTMLInputElement,
  options?: FormUpdateOptions
) {
  options = handleMapButtonClick(
    clickedElement,
    options,
    "filters-form",
    "event",
    "event"
  );
  updateParams(clickedElement);
  updateMapButtonStates();
  if (clickedElement?.classList.contains("select-tree-input")) {
    updateCombinedImpact({ countriesOnly: true });
  } else {
    updateProbabilitiesAndStochastics(options);
  }
};

// Flag to indicate that current action is from a popstate so that changes
// don't get written to the location history
let usingHistory = false;

window.addEventListener("popstate", () => {
  usingHistory = true;
  applyParamsToAllForms(ALL_PAGE_FORMS);
  updateBaseLayer();
  updateProbabilitiesAndStochastics();
  updateMapButtonStates();
  updateTableButtonStates();
  usingHistory = false;
});

const updateParams = (window.updateParams = function updateParams(
  clickedElement?: HTMLSelectElement | HTMLInputElement | undefined
) {
  applyAllFormValuesToParams(ALL_PAGE_FORMS, clickedElement);
});

async function updateProbabilitiesAndStochastics({
  zoomToFit = false,
}: FormUpdateOptions = {}) {
  const paramsGrouped = getParamsGrouped();

  const latitude =
    parseFloat(paramsGrouped.latitude?.join() || ("0" as string)) ||
    INITIAL_LATITUDE;
  const longitude =
    parseFloat(paramsGrouped.longitude?.join() || ("0" as string)) ||
    INITIAL_LONGITUDE;
  const radius =
    parseFloat(paramsGrouped.radius?.join() || ("0" as string)) ||
    INITIAL_RADIUS;
  const colorBy =
    paramsGrouped.color_by?.join() ||
    document
      .querySelector("input[id^=id_metadata_]")
      ?.id?.replace(/^id_metadata_(\w+)__(?:min|max)/, "$1");

  const hazard = paramsGrouped.hazard?.join() ?? null;

  if (hazard === "winterstorm") {
    filter_circle
      .setLatLng([latitude, longitude])
      .setRadius(Math.min(radius, WINTERSTORM_MAXIMUM_RADIUS) * 1000)
      .addTo(LAYERS.search_location_layer!);
  } else {
    LAYERS.search_location_layer!.removeLayer(filter_circle);
  }

  // const tableColumns = paramsGrouped.table_events ?? [];
  const selectedEventIds = Array.from(
    (paramsGrouped.event ?? []) as string | string[]
  )
    .filter(Boolean)
    .map((id) => parseInt(id));
  const filteredEvents = Array.from(
    document.querySelectorAll(
      ".event-list-item"
    ) as NodeListOf<HTMLUListElement>
  )
    .map(
      (element: HTMLUListElement) =>
        ({ ...element.dataset }) as unknown as FilteredEventData &
          Record<string, number | string>
    )
    .filter((event) => event.latitude && event.longitude)
    .map((event) =>
      mapValues(event, (val) =>
        isNaN(val as number) ? val : parseFloat(val as string)
      )
    );

  if (!filteredEvents.length) {
    cleanupLayer(LayerNames.FilteredItems);
  }

  if (!selectedEventIds.length) {
    cleanupLayer(LayerNames.EventFootprint);
  }

  // if (!filteredEvents.length && !selectedEventIds.length) {
  //   return;
  // }

  // Download the shapes, areas, values for the selected countries, in parallel
  const events = await getEventDetail(selectedEventIds);

  // cleanupLayer("region_layer");
  // cleanupLayer(LayerNames.FilteredItems);
  // cleanupLayer(LayerNames.EventFootprint);

  // Domain is reversed so higher values are red
  const palette = (paramsGrouped.colors?.[0] ??
    "RdYlGn") as chroma.BrewerPaletteName;

  const invertColors = paramsGrouped.invert_colors?.[0] ? true : false;

  const quantisation = (paramsGrouped.quantisation?.[0] ??
    "logarithmic") as QuantisationType;

  // updateRegionLayer(geojson);
  updateEventFootprintLayer(events, palette, invertColors, quantisation);

  updateFilteredEventsLayer(
    filteredEvents,
    palette,
    invertColors,
    quantisation,
    colorBy!
  );

  setTimeout(() => {
    if (!zoomToFit) {
      return;
    }

    let zoomFunction: (() => void) | null = null;
    if (zoomToFit === "event") {
      if (events?.some((e) => e.location)) {
        zoomFunction = window.zoomToEvent;
      }
    } else {
      zoomFunction = window.zoomToRegions;
    }
    if (zoomFunction) {
      setTimeout(zoomFunction, 50);
    }
  });
}

window.calculateImpact = async function calculateImpact(event: MouseEvent) {
  const button = event.target as HTMLButtonElement;
  button.classList.add("load-request");
  button.disabled = true;
  updateParams();
  try {
    await updateCombinedImpact();
  } finally {
    button.classList.remove("load-request");
    button.disabled = false;
  }
};

let lastResults: FeatureCollectionSchema | null = null;

export type UpdateCombinedOptions = {
  countriesOnly?: boolean;
};

async function updateCombinedImpact({
  countriesOnly = false,
}: UpdateCombinedOptions = {}) {
  const paramsGrouped = getParamsGrouped();

  // const colorBy =
  //   paramsGrouped.color_by?.join() ||
  //   document
  //     .querySelector("input[id^=id_metadata_]")
  //     ?.id?.replace(/^id_metadata_(\w+)__(?:min|max)/, "$1");

  const countries = (paramsGrouped.countries as CountriesEnum[]) ?? [];
  const tableEvents = countriesOnly
    ? []
    : (paramsGrouped.table_events ?? []).map((val) => parseInt(val));

  if (tableEvents.length !== 2 && !countriesOnly) {
    toast("Please select two events to combine.");
    return;
  }

  // const allColumns = without(
  //   uniq([...tableColumns].flat().filter(Boolean)),
  //   ...SUMMARY_COLUMNS
  // );
  const areas = paramsGrouped.areas ?? [];
  const exposure = paramsGrouped.exposure ?? [];
  const [colorResultsBy] = paramsGrouped.color_results_by ?? [];

  const showAllCountries = countries?.includes("ALL");

  const countriesByAreaCode = getCountriesByAreaCode();

  const countriesIncludingAreas = showAllCountries
    ? ["ALL"]
    : (uniq([
        ...countries,
        ...areas.map((code) => countriesByAreaCode[code]),
      ]) as CountriesEnum[]);

  if (!countries.length && !areas.length && !countriesOnly) {
    alert("Please select at least one region.");
    cleanupLayer(LayerNames.Region);
    return;
  }

  if (!exposure.length && !countriesOnly) {
    alert("Please select an exposure type.");
    cleanupLayer(LayerNames.Region);
    return;
  }

  const bbox = main_map.getBounds().toBBoxString();

  // Download the shapes, areas, values for the selected countries, in parallel
  const [shapes, areaDefinitions, values, events] =
    await fetchCountriesAndCombinedImpacts(
      countriesIncludingAreas as CountriesEnum[],
      tableEvents!,
      bbox,
      exposure![0]!
    );

  if (values) {
    lastResults = values;
  } else if (lastResults) {
    toast("Run calculate again to update results.");
  }

  const eventsMap = keyBy(events ?? [], "id");

  // TODO: do we want to include the current-mapped column in the table or not?
  const { geojson, data } = buildResultsMapAndTableData({
    shapes: shapes ?? [],
    areas,
    areaDefinitions: areaDefinitions ?? {},
    countries,
    tableColumns: RESULT_COLUMNS,
    mapColumns: [],
    eventsMap: eventsMap ?? {},
    values: values ?? lastResults ?? [],
  });

  // If the selected map column is one of the selected table columns, we'll
  // display ALL columns if you click on a NUTS3 region, beginning with the
  // selected one (to ensure that that one has its values displayed in the map).
  // And if there are extra columns (min overlap, max total) we'll display them
  // too.
  // if (
  //   events[0] &&
  //   (tableColumns.includes(events[0]) || SUMMARY_COLUMNS.includes(events[0]))
  // ) {
  //   events = uniq([events[0], ...tableColumns, ...extraColumns]);
  // }

  cleanupLayer(LayerNames.Region);

  // Domain is reversed so higher values are red
  const paletteName = (paramsGrouped.colors?.[0] ??
    "RdYlGn") as chroma.BrewerPaletteName;

  const invertColors = paramsGrouped.invert_colors?.[0] ? true : false;

  const quantisation = (paramsGrouped.quantisation?.[0] ??
    "logarithmic") as QuantisationType;

  const { colors } = showLegend({
    layer: LayerNames.Region,
    position: "topright",
    paletteName,
    quantisation,
    invertColors,
    values: geojson.map(
      (feature) => feature.properties?.columns?.[colorResultsBy!] ?? null
    ),
    title: `Combined impact (TODO UNITS)`,
  });

  updateRegionLayer(
    geojson,
    colors,
    areaDefinitions!,
    eventsMap ?? {},
    colorResultsBy!
  );

  if (!countriesOnly) {
    setTimeout(() => {
      displayDataTable(RESULT_COLUMNS, countries, data, eventsMap, geojson);
    });
  }
}

function updateEventFootprintLayer(
  events: {
    collection_id: number;
    footprint?: string | { [key: string]: unknown } | null;
    footprint_type: string;
    id: number;
    location?: { [key: string]: number } | null;
    hazard?: string;
    hazardLabel?: string;
    unit?: string;
  }[],
  paletteName: chroma.BrewerPaletteName,
  invertColors: boolean,
  quantisation: QuantisationType
) {
  cleanupLayer(LayerNames.Heat);
  cleanupLayer(LayerNames.EventFootprint);
  cleanupLayer(LayerNames.GeoRaster);
  const filteredEvents = events.filter((event) => event.footprint);

  filteredEvents.forEach((event) => {
    if (event.footprint_type === "lazy_py_coord_vals") {
      const values = (event.footprint! as unknown as [number, number, number][])
        .map(([y, x, z]) => z)
        .filter(Boolean);
      const title = `${event.hazardLabel} footprint${event.unit ? ` (${event.unit})` : ""}`;
      const { colors } = showLegend({
        layer: LayerNames.Heat,
        position: "bottomright",
        values,
        paletteName,
        invertColors,
        quantisation,
        title,
        layers: [LAYERS.heat_layer!],
      });

      LAYERS.heat_layer!.options = {
        thresholds: colors.colors().length,
        style: (feature) => {
          return {
            color: colors(feature.geometry.value),
            opacity: 1,
            weight: 0,
            fillOpacity: 1,
          };
        },
        onEachFeature: (feature, layer) => {
          layer.bindPopup(
            `<table><tbody><tr><td>${Math.round(feature.value)}km/h</td></tr></tbody></table>`
          );
        },
      };
      // @ts-ignore
      LAYERS.heat_layer.initialize(
        footprintToCartesian(
          event.footprint as unknown as [number, number, number][]
        ),
        {
          pane: "heatPane",
        }
      );
      return;
    } else if (event.footprint_type === "tiff_ext") {
      const tiffString = event.footprint as string;
      if (!tiffString) {
        return;
      }
      const layerTitle = `${event.hazardLabel} footprint`;
      const legendTitle = `${layerTitle}${event.unit ? ` (${event.unit})` : ""}`;
      setGeoRasterLayer({
        tiffString,
        paletteName,
        invertColors,
        quantisation,
        legendTitle,
        layerTitle,
      });
    } else {
      return LAYERS.event_footprint_layer!.addData(
        event.footprint as unknown as GeometryObject
      );
    }
  });
}

const RESULT_COLUMNS = [
  "impact_data_total",
  "impact_data_max",
  "impact_data_min",
];

const RESULT_COLUMN_TITLES: Record<(typeof RESULT_COLUMNS)[number], string> = {
  impact_data_total: "Total impact",
  impact_data_max: "Max impact",
  impact_data_min: "Min impact",
} as const;

function updateRegionLayer(
  geojson: Feature[],
  colors: chroma.Scale<chroma.Color>,
  areaDefinitions: Record<string, Nuts3AreaSchema>,
  eventsMap: Record<string, DataTableColumnSchema>,
  colorResultsBy: string
) {
  LAYERS.region_layer.options = {
    interactive: true,
    onEachFeature: (_, layer) => {
      layer.on({
        click: async (event) => {
          const areaSidebarTemplate = (
            await import("./area_sidebar_template.jst")
          ).default;
          const { feature } = event.target;
          const area = areaDefinitions[feature.properties.NUTS_ID]!;
          const country = area.country;
          const contents = areaSidebarTemplate({
            area,
            country,
            eventsMap,
            columns: RESULT_COLUMNS,
            columnsMap: RESULT_COLUMN_TITLES,
            properties: feature.properties.columns,
            formatValue: floatTo3Digits,
          });
          const areaDetails = document.getElementById("area-details")!;
          areaDetails.innerHTML = contents;
          areaDetails.scrollIntoView({ behavior: "smooth" });
        },
      });
    },
    style: (feature) => {
      const value = feature?.properties?.columns?.[colorResultsBy];
      if (value == null) {
        return { weight: 1 };
      }
      const color = colors(value);
      if (value != undefined) {
        return { color, weight: 1, fillOpacity: 0.7 };
      }
      return {};
    },
  };

  LAYERS.region_layer
    .addData(geojson as unknown as GeoJsonObject)
    .bindTooltip(({ feature }) => {
      const area = areaDefinitions[feature.properties.NUTS_ID]!;
      return `${area.label}, ${area.country.label}`;
    });
}

function updateFilteredEventsLayer(
  events: Array<FilteredEventData & Record<string, number>>,
  paletteName: chroma.BrewerPaletteName,
  invertColors: boolean,
  quantisation: QuantisationType,
  colorBy: string
) {
  cleanupLayer(LayerNames.FilteredItems);

  const values = events
    .map((event) => event[colorBy] ?? 0)
    .filter((value) => value != null);

  const title = `${events[0]?.hazardLabel} search${colorBy ? ` (${colorBy.replace(/_/g, " ")})` : ""}`;

  const { colors } = showLegend({
    layer: LayerNames.FilteredItems,
    paletteName,
    invertColors,
    quantisation,
    values,
    title,
  });

  const markers = events.map((event) =>
    getHazardMarker(event, colors, colorBy)
      .bindTooltip(() => `${event.hazardLabel} ${event.id}`)
      .on("click", () => {
        const button = document.querySelector(
          `.event-list-item[data-id='${event.id}'] .show-on-map-button`
        ) as HTMLButtonElement | null;
        button?.click();
      })
  );
  markers.forEach((marker) => LAYERS.filtered_items_layer?.addLayer(marker));
}

const MAX_OVERLAP_KEY = "max_overlap";
const MAX_COMBINED_KEY = "max_combined";
const SUMMARY_COLUMNS = [MAX_OVERLAP_KEY, MAX_COMBINED_KEY];

function buildResultsMapAndTableData({
  shapes,
  areas,
  areaDefinitions,
  countries,
  tableColumns,
  mapColumns,
  eventsMap,
  values,
}: {
  shapes: ShapeFeature[];
  areas: string[];
  areaDefinitions: Record<string, Nuts3AreaSchema>;
  countries: CountriesEnum[];
  tableColumns: string[];
  mapColumns: string[];
  events: HrscEventSchema[];
  eventsMap: Dictionary<HrscEventSchema>;
  values: FeatureCollectionSchema | null;
}): {
  geojson: Feature[];
  eventGeojson: Feature[];
  data: Array<TableDatum>;
  extraColumns: string[];
  min: number;
  max: number;
} {
  const geojson: Feature[] = [];
  const eventGeojson: Feature[] = [];
  const data: Array<TableDatum> = [];
  const min: number = 0;
  const max: number = 0;
  const extraColumns: string[] = [];

  const valuesByKey = keyBy(values.features, (v) => v.properties.NUTS_ID);

  // if (tableColumns.length === 2) {
  //   const [column1, column2] = tableColumns.map((key) => eventsMap[key]) as [
  //     DataTableColumnSchema,
  //     DataTableColumnSchema,
  //   ];
  //   if (column1.exposure!.key === column2.exposure!.key) {
  //     extraColumns = SUMMARY_COLUMNS;
  //   }
  // }

  // extraColumns.forEach((key) => {
  //   eventsMap[key] = {
  //     key,
  //     label: key,
  //     description: "",
  //   };
  // });

  const isMappingSummaryColumn = SUMMARY_COLUMNS.includes(mapColumns[0]!);
  // const allPrimaryColumns = isMappingSummaryColumn
  //   ? tableColumns
  //   : uniq([...mapColumns, ...tableColumns]);

  for (const shape of shapes) {
    if (!shape) {
      continue;
    }
    const code = shape.properties.NUTS_ID;

    /*
    Because we fetch shapes, areas and data for a whole country (for better
    caching, there may be shapes that we don't want to display, so filter to them
    out if they don't match the original country/area lists.
    */
    if (
      !countries.includes("ALL") &&
      !areas.includes(code) &&
      !(
        areaDefinitions[code] &&
        countries.includes(
          areaDefinitions[code].country.country_code as CountriesEnum
        )
      )
    ) {
      continue;
    }

    // const ZeroColumnValues = values?.features?.length
    //   ? tableColumns.reduce((acc, key) => ({ ...acc, [key]: 0 }), {})
    //   : {};

    if (tableColumns.length && areaDefinitions[code]) {
      const regionValues: Record<string, number> = pick(
        valuesByKey[code]?.properties,
        tableColumns
      );
      // if (!Object.keys(regionValues).length) {
      //   regionValues = ZeroColumnValues;
      // }
      const datum = {
        region: areaDefinitions[code] as Nuts3AreaSchema,
        ...regionValues,
      } as TableDatum;
      data.push(datum);
      const geo = {
        ...shape,
        properties: {
          ...shape.properties,
          // value: primaryValue,
          columns: regionValues,
        },
      };
      geojson.push(geo);
    }
  }
  return { geojson, eventGeojson, data };
}

function fetchCountriesAndCombinedImpacts(
  countriesIncludingAreas: CountriesEnum[],
  eventIds: number[],
  bbox: string,
  exposureKey: string
): Promise<
  [
    ShapeFeature[] | null,
    Record<string, Nuts3AreaSchema> | null,
    FeatureCollectionSchema | null,
    HrscEventSchema[] | null,
  ]
> {
  return Promise.all([
    getShapesList(countriesIncludingAreas),
    getAreasMap(countriesIncludingAreas),
    eventIds.length
      ? getCombinedImpact(eventIds, bbox, countriesIncludingAreas, exposureKey)
      : null,
    eventIds.length ? getEventDetail(eventIds) : [],
  ]);
}

function displayDataTable(
  columns: (keyof typeof RESULT_COLUMN_TITLES)[],
  countries: string[],
  data: TableDatum[],
  eventsMap: Record<string, DataTableColumnSchema>,
  geojson: Feature[]
) {
  const createAreaCellOnClick = (
    cell: HTMLTableCellElement,
    _cellData: string,
    rowData: TableDatum,
    row: number
    // _col: number
  ) =>
    cell.addEventListener("click", async () => {
      const areaSidebarTemplate = (await import("./area_sidebar_template.jst"))
        .default;
      const area = rowData.region!;
      const country = area.country;
      const contents = areaSidebarTemplate({
        area,
        country,
        eventsMap,
        columns,
        properties: geojson[row]!.properties.columns,
      });
      const areaDetails = document.getElementById("area-details")!;
      areaDetails.innerHTML = contents;
      areaDetails.scrollIntoView({ behavior: "smooth" });
    });
  const column_spec: ConfigColumns[] = [
    {
      data: "region.key",
      title: "Code",
      width: "50px",
      createdCell: createAreaCellOnClick,
      className: "pointer",
    },
    {
      data: "region.label",
      title: "Region",
      createdCell: createAreaCellOnClick,
      className: "pointer",
    },
    {
      data: "region.country.country_code",
      title: "Country Code",
      width: "150px",
    },
    { data: "region.country.label", title: "Country" },
    ...columns.map((column: keyof typeof RESULT_COLUMN_TITLES) => ({
      data: (val: TableDatum) => val[column] ?? null,
      title: RESULT_COLUMN_TITLES[column],
      searchable: false,
    })),
  ];
  if (values_table) {
    values_table.destroy();
    jQuery("#values-table").empty();
  }
  const title = `Multi-hazard scenarios for ${countries.join(", ")} (${columns})`;

  values_table = new DataTable("#values-table", {
    layout: {
      topStart: "search",
      topEnd: {
        buttons: [
          "copy",
          {
            extend: "excel",
            filename: title,
            title: title,
          },
          {
            extend: "csv",
            filename: title,
          },
          {
            text: "GeoJSON",
            action: () => getGeoJSON(geojson),
          },
        ],
      } as DataTableFeature,
      bottomStart: "info",
    },
    paging: false,
    scrollX: true,
    scrollY: "25vh",
    data: data,
    columns: column_spec,
  });
}

const baseLayerInput = document.getElementById(
  "id_base_layer"
) as HTMLInputElement;
main_map.addEventListener("baselayerchange", (event: LayersControlEvent) => {
  baseLayerInput.value = event.name;
  if (!usingHistory) {
    updateParams();
  }
});

resetSelectTreeIndeterminate();
updateProbabilitiesAndStochastics();

window.closeAreaPanel = function closeAreaPanel() {
  [
    "area-details",
    // "pin-name-title-0",
    // "column-details-inner",
  ].forEach((id) => {
    const element = document.getElementById(id);
    if (element) {
      element.innerHTML = "";
    }
  });
};

// window.setFilters = async function setFilters() {
//   const sourceTable = document.querySelector(`#column-details-table`);
//   let targetForm = document.querySelector(`#filters-form`) as HTMLFormElement;
//   if (!sourceTable || !targetForm) {
//     return;
//   }
//   const values: Record<string, string> = {};
//   for (const th of sourceTable.querySelectorAll("th")) {
//     const name = th.dataset["name"];
//     if (name && targetForm[name]) {
//       const value = th.dataset["value"];
//       values[name] = value!;
//     }
//   }
//   if (values.hazard !== targetForm.hazard.value) {
//     targetForm.hazard.value = values.hazard!;
//     targetForm.hazard.dispatchEvent(new Event("change"));
//     await new Promise((resolve) => {
//       // Use parent element because the form itself will be replaced
//       targetForm.parentElement!.addEventListener(
//         "htmx:afterSettle",
//         (evt: CustomEvent<{ elt: HTMLElement }>) => {
//           if (evt.detail?.elt!.id === "filters-form") {
//             targetForm = evt.detail.elt as HTMLFormElement;
//             return resolve(true);
//           }
//         },
//         { once: true }
//       );
//     });
//   }
//   for (const key in values) {
//     (targetForm[key] as HTMLSelectElement).value = values[key]!;
//   }
//   targetForm.hazard.dispatchEvent(new Event("change"));
// };

window.toggleTable = function toggleTable(key: string, label: string) {
  const tableId = "table-events";
  const pinLabel = document
    .querySelector(`.pin-label-${slugify(key)}`)
    ?.textContent?.trim();
  const textTemplate = document
    .getElementById("table-events-list-item-template")!
    .innerHTML.replace(/\bEVENTKEY\b/g, key)
    .replace(/\bEVENTLABEL\b/g, label);
  const templateElement = document.createElement("template");
  templateElement.innerHTML = textTemplate;
  const pinLabelElement = templateElement.content.querySelector(".pin-label");
  if (pinLabelElement && pinLabel) {
    pinLabelElement.textContent = pinLabel;
  }
  toggleSelectArray(tableId, key, templateElement.content);
  updateTableButtonStates();
  document.getElementById(tableId)!.closest("details")!.open = true;
  window.formUpdate();
};

window.sortColumn = function sortColumn(key: string, direction: "up" | "down") {
  const id = "table-events";
  reorderSelectArrayValues(id, key, direction);
  window.formUpdate();
};

async function getGeoJSON(features: components["schemas"]["ShapeFeature"][]) {
  const data = {
    type: "FeatureCollection",
    features,
  };
  createGeoJSONDownload(data, "combined_scenario");
}

window.searchHere = function searchHere() {
  const bounds: L.LatLngBounds = main_map.getBounds();
  const center: L.LatLng = main_map.getCenter();
  const width = bounds.getNorthWest().distanceTo(bounds.getNorthEast());
  const height = bounds.getNorthWest().distanceTo(bounds.getSouthWest());
  // Half the max of width/height, converted to kilometres
  const radius = Math.ceil(Math.max(width, height) * 0.0005);
  const filtersForm = document.getElementById(
    "filters-form"
  ) as HTMLFormElement;
  filtersForm.latitude.value = center.lat;
  filtersForm.longitude.value = center.lng;
  filtersForm.radius.value = radius;
  window.formUpdate(undefined, { zoomToFit: false });
};

window.htmx.on("htmx:afterSwap", () => {
  updateTableButtonStates();
  updateMapButtonStates();
});

updateTableButtonStates();
updateMapButtonStates();
updateCombinedImpact({ countriesOnly: true });
