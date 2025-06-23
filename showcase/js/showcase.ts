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

import type {
  Feature,
  GeoJsonObject,
  GeoJsonProperties,
  Geometry,
} from "geojson";

import chroma from "chroma-js";
import "../../shared/js/leaflet_grayscale";

import "@gnatih/leaflet.legend";
import { LayersControlEvent } from "leaflet";
import { sortBy, uniq } from "lodash";
import {
  DataTableColumnSchema,
  Nuts3AreaSchema,
  ShapeFeature,
  type CountriesEnum,
} from "../../data/types/api";
import { BaseMaps } from "../../shared/js/base_map_layers";
import {
  applyFormValuesToParams,
  applyParamsToAllForms,
  getCountriesByAreaCode,
  getParamsGrouped,
  resetSelectTreeIndeterminate,
  toggleSelectArray,
} from "../../shared/js/dom_tools";
import {
  createMap,
  FormUpdateOptions,
  handleMapButtonClick,
  LayerNames,
  QuantisationType,
} from "../../shared/js/map_tools";
import { TableDatum } from "../../shared/js/types";
import { createGeoJSONDownload } from "../../shared/js/utils";
import {
  downloadGeoJSON,
  getAreasMap,
  getColumnsMap,
  getShapesList,
  getValuesMap,
} from "./showcase_api";

declare global {
  interface Window {
    formUpdate: (
      clickedElement?: HTMLSelectElement | HTMLInputElement,
      options?: FormUpdateOptions
    ) => void;
    closeAreaPanel: () => void;
    updateParams: () => void;
    setFilters: () => Promise<void>;
    toggleTable: (key: string) => void;
    sortColumn: (key: string, direction: "up" | "down") => void;
  }
}

// window.htmx.logAll();

let values_table: DataTableApi | null = null;

const options = document.getElementById("showcase_script")!.dataset;
const INITIAL_LATITUDE = parseFloat(options.latitude ?? "0");
const INITIAL_LONGITUDE = parseFloat(options.longitude ?? "0");
const DISPLAYED_COUNTRIES = JSON.parse(
  document.getElementById("displayed-countries")?.textContent ?? "null"
) ?? ["ALL"];
export const INITIAL_BASELAYER =
  ((document.getElementById("id_base_layer") as HTMLInputElement)
    .value as keyof typeof BaseMaps) || "Greyscale";

const {
  main_map,
  LAYERS,
  hideLegend,
  showLegend,
  cleanupLayer,
  updateBaseLayer,
  returnHome,
  updateMapButtonStates,
  updateTableButtonStates,
} = createMap({
  initialBaselayer: INITIAL_BASELAYER,
  latitude: INITIAL_LATITUDE,
  longitude: INITIAL_LONGITUDE,
  itemFieldName: "column",
  tableSelectElementId: "table-columns",
  tableSelectButtonClass: "table-column-button",
  layers: {
    [LayerNames.Region]: "Regions",
  },
});

window.formUpdate = function formUpdate(
  clickedElement?: HTMLSelectElement | HTMLInputElement,
  options?: FormUpdateOptions
) {
  handleMapButtonClick(clickedElement, options, "filters-form", "column");
  updateParams(clickedElement);
  updateMapButtonStates();
  updateMapAndTable(options);
};

// Flag to indicate that current action is from a popstate so that changes
// don't get written to the location history
let usingHistory = false;

window.addEventListener("popstate", () => {
  usingHistory = true;
  applyParamsToAllForms([
    "filters-form",
    "settings-form",
    "regions-form",
    "table-datasets-form",
  ]);
  updateMapAndTable();
  updateBaseLayer();
  usingHistory = false;
});

const updateParams = (window.updateParams = function updateParams(
  clickedElement?: HTMLSelectElement | HTMLInputElement | undefined
) {
  const settingsForm = document.getElementById(
    "settings-form"
  ) as HTMLFormElement;
  const filtersForm = document.getElementById(
    "filters-form"
  ) as HTMLFormElement;
  const regionsForm = document.getElementById(
    "regions-form"
  ) as HTMLFormElement;
  const tableDatasetsForm = document.getElementById(
    "table-datasets-form"
  ) as HTMLFormElement;
  applyFormValuesToParams(
    [filtersForm, regionsForm, settingsForm, tableDatasetsForm],
    clickedElement
  );
});

const FootprintColumns: Record<HazardTypes, string | null> = {
  flood: "fp_fl",
  EQ: "fp_eq",
  EQ_flood: null,
};

function getLegendTitle(column: string) {
  switch (column) {
    case "fp_eq":
      return "Ground motion (g)";
    case "fp_fl":
      return "Flood water depth (m)";
    default:
      return "Impact (million Euro)";
  }
}

type HazardTypes = "flood" | "EQ" | "EQ_flood";

function getColumnName(hazard: HazardTypes, code: string): string | null {
  let prefix: string = hazard?.toLocaleLowerCase();
  if (hazard === "EQ_flood") {
    prefix = "total";
    if (code === "fp") {
      return null;
    }
  }
  let key;
  if (code === "fp") {
    key = FootprintColumns[hazard]!;
    if (!key) {
      return null;
    }
  } else {
    key = `${prefix}_${code}`;
  }

  return key; // `Danube_multi_hazard_scenario_A21_${key}`;
}

async function updateMapAndTable(options: FormUpdateOptions = {}) {
  const paramsGrouped = getParamsGrouped();

  const countries = (paramsGrouped.countries as CountriesEnum[]) ?? ["ALL"];

  const hazard = Array.from(
    (paramsGrouped.hazard as HazardTypes | HazardTypes[]) ?? ["EQ"]
  ).filter(Boolean)[0] as HazardTypes;

  const hazards: HazardTypes[] =
    hazard === "EQ_flood" ? ["EQ", "flood", "EQ_flood"] : [hazard];

  // Always show footprints first, then other valuesin alphabetical order
  const tableColumnCodes = sortBy(paramsGrouped.table_columns ?? [], (col) =>
    col === "fp" ? "" : col
  ).filter((col) => /^(fp|[A-S])$/.test(col));

  const columns = Array.from(
    (paramsGrouped.column ?? ["fp"]) as string | string[]
  ).filter(Boolean);

  const tableColumns = uniq(tableColumnCodes)
    .map((code) => hazards.map((h) => getColumnName(h, code)))
    .flat()
    .filter(Boolean) as string[];

  const mapColumns: string[] = columns
    .map((column) => getColumnName(hazard, column)!)
    .filter(Boolean);

  const allColumns = uniq(
    [mapColumns, tableColumns].flat().filter(Boolean)
  ) as string[];

  const detailArea = (paramsGrouped.detail_area ?? [])[0] ?? null;

  const areas = paramsGrouped.areas ?? [];

  const showAllCountries = countries?.includes("ALL");

  const countriesByAreaCode = getCountriesByAreaCode();

  const countriesIncludingAreas: Array<CountriesEnum | "ALL"> = showAllCountries
    ? DISPLAYED_COUNTRIES
    : (uniq([
        ...countries,
        ...areas.map((code) => countriesByAreaCode[code]),
      ]) as CountriesEnum[]);

  if (!countries.length && !areas.length) {
    cleanupLayer(LayerNames.Region);
    hideLegend();
    returnHome();
    return;
  }

  // Download the shapes, areas, values for the selected countries, in parallel
  const [shapes, areaDefinitions, columnsMap, values] = await fetchMapResources(
    allColumns,
    countriesIncludingAreas
  );
  if (!shapes || !Object.keys(shapes).length) {
    window.toast(`Sorry, no outlines found for ${countries.join(", ")}`);
    return;
  }
  if (!areaDefinitions || !Object.keys(areaDefinitions).length) {
    window.toast(`Sorry, no areas found for ${countries.join(", ")}`);
    return;
  }
  if (!columnsMap || !Object.keys(shapes).length) {
    window.toast(`Sorry, no matching column definitions found`);
    // Don't return, can still draw the map
  }
  if (tableColumns.length && (!values?.length || !Object.keys(values).length)) {
    window.toast(
      `Sorry, no values found for ${countries.join(", ")} and ${tableColumns}`
    );
    // Don't return, can still draw the map
  }

  const { geojson, data, extraColumns } = buildMapAndTableData({
    shapes,
    areas,
    areaDefinitions,
    countries,
    tableColumns,
    mapColumns,
    values,
  });

  // Domain is reversed so higher values are red
  const paletteName = (paramsGrouped.colors?.[0] ??
    "RdYlGn") as chroma.BrewerPaletteName;

  const invertColors = paramsGrouped.invert_colors?.[0] ? true : false;

  const quantisation = (paramsGrouped.quantisation?.[0] ??
    "logarithmic") as QuantisationType;

  const areaDetails = document.getElementById(
    "area-details"
  ) as HTMLInputElement;
  if (detailArea) {
    const feature = geojson.find(
      (geo) => geo?.properties?.NUTS_ID === detailArea
    );
    if (feature) {
      const areaSidebarTemplate = (await import("./area_sidebar_template.ejs"))
        .default;
      const area = areaDefinitions[feature.properties!.NUTS_ID]!;
      const country = area.country;
      const contents = areaSidebarTemplate({
        area,
        country,
        columnsMap,
        columns: tableColumns,
        properties: feature!.properties,
        prettyColumnTitle,
      });

      areaDetails.innerHTML = contents;
    } else {
      areaDetails.innerHTML = "";
    }
  } else {
    areaDetails.innerHTML = "";
  }

  if (options.areaDetailOnly) {
    return;
  }

  const shouldUpdateMap = !options.areaDetailOnly && mapColumns[0];

  if (shouldUpdateMap) {
    const { colors } = showLegend({
      paletteName,
      quantisation,
      invertColors,
      values: geojson.map((feature) => feature.properties?.value),
      title: getLegendTitle(mapColumns[0]!),
    });

    updateRegionLayer(geojson, colors, areaDefinitions);
  }

  setTimeout(() => {
    displayDataTable(
      [...tableColumns, ...extraColumns],
      countries,
      data,
      columnsMap ?? {},
      geojson
    );
    if (shouldUpdateMap) {
      setTimeout(
        () =>
          main_map.invalidateSize().fitBounds(LAYERS.region_layer!.getBounds()),
        50
      );
    }
  });
}

function updateRegionLayer(
  geojson: Feature[],
  colors: chroma.Scale<chroma.Color> | null,
  areaDefinitions: Record<string, Nuts3AreaSchema>
) {
  cleanupLayer(LayerNames.Region);
  LAYERS.region_layer!.options = {
    interactive: true,
    onEachFeature: (_, layer) => {
      layer.on({
        click: async (event) => {
          const detailAreaField = document.getElementById(
            "id_detail_area"
          ) as HTMLInputElement;
          detailAreaField.value = event.target.feature.properties.NUTS_ID;
          window.formUpdate(null, { areaDetailOnly: true });
        },
      });
    },
    style: (feature) => {
      if (feature?.properties?.value == null) {
        return { weight: 1 };
      }
      const { value } = feature.properties;
      if (colors && value != undefined) {
        const color = colors(value ?? 0).toString();
        return { color, weight: 1, fillOpacity: 0.7 };
      }
      return {};
    },
  };

  LAYERS.region_layer!.addData(geojson as unknown as GeoJsonObject).bindTooltip(
    ({ feature }) => {
      const area = areaDefinitions[feature.properties.NUTS_ID]!;
      return `${area.label}, ${area.country.label}`;
    }
  );
}

function buildMapAndTableData({
  shapes,
  areas,
  areaDefinitions,
  countries,
  tableColumns,
  mapColumns,
  values,
}: {
  shapes: ShapeFeature[];
  areas: string[];
  areaDefinitions: Record<string, Nuts3AreaSchema>;
  countries: CountriesEnum[];
  tableColumns: string[];
  mapColumns: string[];
  values: Array<Record<string, Record<string, number>> | null> | null;
}): {
  geojson: Feature[];
  data: Array<TableDatum>;
  extraColumns: string[];
} {
  const geojson: Feature[] = [];
  const data: Array<TableDatum> = [];
  const extraColumns: string[] = [];

  const allPrimaryColumns = uniq([...mapColumns, ...tableColumns]);

  for (const shape of shapes) {
    if (!shape) {
      continue;
    }
    const code = shape.properties.NUTS_ID as string;

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

    if (allPrimaryColumns.length && areaDefinitions[code]) {
      const datum = {
        region: areaDefinitions[code] as Nuts3AreaSchema,
      } as TableDatum;
      data.push(datum);

      const region_values: Record<string, number> = {};
      let geo: Feature;

      allPrimaryColumns.forEach((column: string, i: number) => {
        const value = values?.[i]?.[column]?.[code] ?? 0;

        datum[column] = region_values[column] = value;

        if (i === 0) {
          const primaryValue = value;

          geo = {
            ...shape,
            properties: {
              ...shape.properties,
              value: primaryValue,
              columns: region_values,
            },
          } as Feature<Geometry, GeoJsonProperties>;

          geojson.push(geo);
        }
      });
    } else {
      geojson.push(shape as Feature);
    }
  }
  return { geojson, data, extraColumns };
}

function fetchMapResources(
  columns: string[],
  countriesIncludingAreas: CountriesEnum[]
) {
  return Promise.all([
    getShapesList(countriesIncludingAreas),
    getAreasMap(countriesIncludingAreas),
    getColumnsMap(columns),
    columns.length
      ? Promise.all(
          columns.map((column) => getValuesMap(countriesIncludingAreas, column))
        )
      : null,
  ]);
}

function displayDataTable(
  columns: string[],
  countries: string[],
  data: TableDatum[],
  columnsMap: Record<string, DataTableColumnSchema>,
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
      const detailAreaField = document.getElementById(
        "id_detail_area"
      ) as HTMLInputElement;
      detailAreaField.value = geojson[row]!.properties!.NUTS_ID;
      window.formUpdate(null, { areaDetailOnly: true });
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
    ...columns.map((column) => ({
      data: (val: TableDatum) => val[column] ?? null,
      title: prettyColumnTitle(column),
      searchable: false,
    })),
  ];

  if (values_table) {
    values_table.destroy();
    jQuery("#values-table").empty();
  }

  const title = `Scenario showcase for ${countries.join(", ")} (${columns})`;

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
            action: getGeoJSON,
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
updateMapAndTable();

window.closeAreaPanel = function closeAreaPanel() {
  ["area-details"].forEach((id) => {
    const element = document.getElementById(id);
    if (element) {
      element.innerHTML = "";
    }
  });
};

window.setFilters = async function setFilters() {
  const sourceTable = document.querySelector(`#column-details-table`);
  let targetForm = document.querySelector(`#filters-form`) as HTMLFormElement;
  if (!sourceTable || !targetForm) {
    return;
  }
  const values: Record<string, string> = {};
  for (const th of sourceTable.querySelectorAll("th")) {
    const name = th.dataset["name"];
    if (name && targetForm[name]) {
      const value = th.dataset["value"];
      values[name] = value!;
    }
  }

  if (values.hazard !== targetForm.hazard.value) {
    targetForm.hazard.value = values.hazard!;
    targetForm.hazard.dispatchEvent(new Event("change"));
    await new Promise((resolve) => {
      // Use parent element because the form itself will be replaced
      targetForm.parentElement!.addEventListener(
        "htmx:afterSettle",
        (evt: CustomEvent<{ elt: HTMLElement }>) => {
          if (evt.detail?.elt!.id === "filters-form") {
            targetForm = evt.detail.elt as HTMLFormElement;
            return resolve(true);
          }
        },
        { once: true }
      );
    });
  }

  for (const key in values) {
    (targetForm[key] as HTMLSelectElement).value = values[key]!;
  }

  targetForm.hazard.dispatchEvent(new Event("change"));
};

window.toggleTable = function toggleTable(key: string) {
  const id = "table-columns";
  const selectedKeys: string[] = toggleSelectArray(id, key);
  updateTableButtonStates();
  const params = getParamsGrouped();
  const [mapColumn] = params.column ?? [];
  // Make sure that the map displays a column that's selected to display in table
  if (
    selectedKeys.includes(key) &&
    (!mapColumn || (mapColumn !== "fp" && !selectedKeys.includes(mapColumn)))
  ) {
    // This will trigger displaying the map and also trigger formUpdate()
    // so no need to do it below
    (
      document.querySelector(
        `button.show-on-map-button[value=${key}]`
      ) as HTMLButtonElement
    ).click();
    return;
  } else {
    window.formUpdate();
  }
};

function prettyColumnTitle(column: string): string {
  return column
    .replace(/_/g, " ")
    .replace(/^fp\s(.+)$/, "$1 Footprint")
    .replace(/\btotal\b/, "Total")
    .replace(/\b(fl|flood)\b/, "Flood")
    .replace(/\beq\b/, "Earthquake");
}

async function getGeoJSON() {
  const params = getParamsGrouped();
  const countries = params.countries as Array<CountriesEnum | "ALL">;
  const areas = params.areas;
  const columns = params.table_columns;

  const data = await downloadGeoJSON({ countries, areas, columns });
  if (data) {
    createGeoJSONDownload(data, "myriad_multi_hazard_showcase.geojson");
  }
}

window.htmx.on("htmx:afterSwap", () => {
  updateTableButtonStates();
  updateMapButtonStates();
});

updateTableButtonStates();
updateMapButtonStates();
