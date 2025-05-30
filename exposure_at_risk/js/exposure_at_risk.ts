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

import type { Feature, GeoJsonObject } from "geojson";

import chroma from "chroma-js";
import "../../shared/js/leaflet_grayscale";

import "@gnatih/leaflet.legend";
import { LayersControlEvent } from "leaflet";
import { uniq, without } from "lodash";
import {
  components,
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
  reorderSelectArrayValues,
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
import { createGeoJSONDownload, slugify } from "../../shared/js/utils";
import {
  downloadGeoJSON,
  getAreasMap,
  getColumnsMap,
  getShapesList,
  getValuesMap,
} from "./exposure_at_risk_api";
import { TableDatum } from "./types";
import { createDataTableReferencesButtonArray } from "../../shared/js/table_utils";

declare global {
  interface Window {
    formUpdate: () => void;
    closeAreaPanel: () => void;
    updateParams: () => void;
    setFilters: () => Promise<void>;
    toggleTable: (key: string) => void;
    sortColumn: (key: string, direction: "up" | "down") => void;
  }
}

// window.htmx.logAll();

let values_table: DataTableApi | null = null;

const options = document.getElementById("exposure_at_risk_script")!.dataset;
const INITIAL_LATITUDE = parseFloat(options.latitude ?? "0");
const INITIAL_LONGITUDE = parseFloat(options.longitude ?? "0");
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
  zoomTo,
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
  options = handleMapButtonClick(
    clickedElement,
    options,
    "filters-form",
    "column",
    "column"
  );
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

async function updateMapAndTable({
  zoomToFit = "auto",
}: FormUpdateOptions = {}) {
  const paramsGrouped = getParamsGrouped();

  const countries = (paramsGrouped.countries as CountriesEnum[]) ?? [];
  const tableColumns = paramsGrouped.table_columns ?? [];
  let mapColumns = Array.from(
    (paramsGrouped.column ?? []) as string | string[]
  ).filter(Boolean);
  const allColumns = without(
    uniq([mapColumns, ...tableColumns].flat().filter(Boolean)),
    ...SUMMARY_COLUMNS
  );
  const areas = paramsGrouped.areas ?? [];

  const showAllCountries = countries?.includes("ALL");

  const countriesByAreaCode = getCountriesByAreaCode();

  const countriesIncludingAreas: Array<CountriesEnum | "ALL"> = showAllCountries
    ? ["ALL"]
    : (uniq([
        ...countries,
        ...areas.map((code) => countriesByAreaCode[code]),
      ]) as CountriesEnum[]);

  if (!countries.length && !areas.length) {
    cleanupLayer("region_layer");
    hideLegend();
    returnHome();
    return;
  }

  // Download the shapes, areas, values for the selected countries, in parallel
  const [shapes, areaDefinitions, columnsMap, values] = await fetchMapResources(
    allColumns,
    countriesIncludingAreas
  );
  if (!columnsMap || !Object.keys(shapes).length) {
    window.toast(`Sorry, no matching column definitions found`);
    return;
  }
  if (!shapes || !Object.keys(shapes).length) {
    window.toast(`Sorry, no outlines found for ${countries.join(", ")}`);
    return;
  }
  if (!areaDefinitions || !Object.keys(areaDefinitions).length) {
    window.toast(`Sorry, no areas found for ${countries.join(", ")}`);
    return;
  }
  if (tableColumns.length && (!values?.length || !Object.keys(values).length)) {
    window.toast(
      `Sorry, no values found for ${countries.join(", ")} and ${tableColumns}`
    );
    // Don't return, can still draw the map
  }

  // TODO: do we want to include the current-mapped column in the table or not?
  const { geojson, data, extraColumns, min, max } = buildMapAndTableData({
    shapes,
    areas,
    areaDefinitions,
    countries,
    tableColumns,
    mapColumns,
    columnsMap,
    values,
  });

  // If the selected map column is one of the selected table columns, we'll
  // display ALL columns if you click on a NUTS3 region, beginning with the
  // selected one (to ensure that that one has its values displayed in the map).
  // And if there are extra columns (min overlap, max total) we'll display them
  // too.
  if (
    mapColumns[0] &&
    (tableColumns.includes(mapColumns[0]) ||
      SUMMARY_COLUMNS.includes(mapColumns[0]))
  ) {
    mapColumns = uniq([mapColumns[0], ...tableColumns, ...extraColumns]);
  }

  cleanupLayer("region_layer");

  // Domain is reversed so higher values are red
  const paletteName = (paramsGrouped.colors?.[0] ??
    "RdYlGn") as chroma.BrewerPaletteName;

  const quantisation = (paramsGrouped.quantisation?.[0] ??
    "logarithmic") as QuantisationType;

  const invertColors = paramsGrouped.invert_colors?.[0] ? true : false;

  const mapUnits = columnsMap[mapColumns[0] ?? ""]?.exposure?.unit ?? null;

  const { colors } = showLegend({
    paletteName,
    quantisation,
    invertColors,
    values: geojson.map((feature) => feature.properties?.value ?? null),
    title: mapUnits ? `Exposure (${mapUnits})` : "Exposure",
  });

  updateRegionLayer(geojson, colors, areaDefinitions, columnsMap, mapColumns);

  setTimeout(() => {
    displayDataTable(
      [...tableColumns, ...extraColumns],
      countries,
      data,
      columnsMap,
      geojson
    );
    setTimeout(
      () =>
        main_map.invalidateSize().fitBounds(LAYERS.region_layer.getBounds()),
      50
    );
  });
}

function updateRegionLayer(
  geojson: Feature[],
  colors: chroma.Scale<chroma.Color>,
  areaDefinitions: Record<string, Nuts3AreaSchema>,
  columnsMap: Record<string, DataTableColumnSchema>,
  columns: string[]
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
            columnsMap,
            columns,
            properties: feature.properties,
            showThreshold: columns.some(
              (column) => columnsMap[column]?.threshold
            ),
            showReturnPeriod: columns.some(
              (column) => columnsMap[column]?.return_period
            ),
          });
          const areaDetails = document.getElementById("area-details")!;
          areaDetails.innerHTML = contents;
          areaDetails.scrollIntoView({ behavior: "smooth" });
        },
      });
    },
    style: (feature) => {
      if (feature?.properties?.value == null) {
        return { weight: 1 };
      }
      const { value } = feature.properties;
      const color = colors(feature.properties.value);
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

const MAX_OVERLAP_KEY = "max_overlap";
const MAX_COMBINED_KEY = "max_combined";
const SUMMARY_COLUMNS = [MAX_OVERLAP_KEY, MAX_COMBINED_KEY];

function buildMapAndTableData({
  shapes,
  areas,
  areaDefinitions,
  countries,
  tableColumns,
  mapColumns,
  columnsMap,
  values,
}: {
  shapes: ShapeFeature[];
  areas: string[];
  areaDefinitions: Record<string, Nuts3AreaSchema>;
  countries: CountriesEnum[];
  tableColumns: string[];
  mapColumns: string[];
  columnsMap: Record<string, DataTableColumnSchema>;
  values: Array<Record<string, Record<string, number>> | null> | null;
}): {
  geojson: Feature[];
  data: Array<TableDatum>;
  extraColumns: string[];
  min: number;
  max: number;
} {
  const geojson: Feature[] = [];
  const data: Array<TableDatum> = [];
  let min: number = 0;
  let max: number = 0;
  let extraColumns: string[] = [];

  if (tableColumns.length === 2) {
    const [column1, column2] = tableColumns.map((key) => columnsMap[key]) as [
      DataTableColumnSchema,
      DataTableColumnSchema,
    ];
    if (column1.exposure!.key === column2.exposure!.key) {
      extraColumns = SUMMARY_COLUMNS;
    }
  }

  extraColumns.forEach((key) => {
    columnsMap[key] = {
      key,
      label: key,
      description: "",
    };
  });

  const isMappingSummaryColumn = SUMMARY_COLUMNS.includes(mapColumns[0]!);
  // const allPrimaryColumns = isMappingSummaryColumn
  //   ? tableColumns
  //   : uniq([...mapColumns, ...tableColumns]);
  const allPrimaryColumns = uniq([...mapColumns, ...tableColumns]);

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

    if (allPrimaryColumns.length && areaDefinitions[code]) {
      const datum = {
        region: areaDefinitions[code] as Nuts3AreaSchema,
      } as TableDatum;
      const region_values: Record<string, number> = {};
      let geo: Feature;

      // extraColumns will only exist if there are exactly two data columns
      // with matching exposure types
      extraColumns.forEach((column: string) => {
        const val0 = values?.[0]?.[tableColumns[0]!]?.[code] ?? 0;
        const val1 = values?.[1]?.[tableColumns[1]!]?.[code] ?? 0;
        const value =
          column === MAX_OVERLAP_KEY
            ? Math.min(val0, val1)
            : // TODO Math.min with area total exposure once available
              val0 + val1;
        datum[column] = region_values[column] = value;
      });

      allPrimaryColumns.forEach((column: string, i: number) => {
        const value = values?.[i]?.[column]?.[code] ?? 0;

        datum[column] = region_values[column] = value;
        if (i === 0) {
          const primaryValue = isMappingSummaryColumn
            ? datum[mapColumns[0]!]!
            : value;
          /*
          Only calculate max/min based on the first column (which, if
          selected, will be the map column), and add the data to the table/
          geojson arrays once only (other columns will be added to the 
          objects after they have been appeanded to the arrays).
          */
          if (primaryValue < min) {
            min = primaryValue;
          }
          if (primaryValue > max) {
            max = primaryValue;
          }
          data.push(datum);
          geo = {
            ...shape,
            properties: {
              ...shape.properties,
              value: primaryValue,
              columns: region_values,
            },
          };
          geojson.push(geo);
        }
      });
    } else {
      geojson.push(shape);
    }
  }
  return { geojson, data, extraColumns, max, min };
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
      const areaSidebarTemplate = (await import("./area_sidebar_template.jst"))
        .default;
      const area = rowData.region!;
      const country = area.country;
      const contents = areaSidebarTemplate({
        area,
        country,
        columnsMap,
        columns,
        properties: geojson[row]!.properties,
        showThreshold: columns.some((column) => columnsMap[column]?.threshold),
        showReturnPeriod: columns.some(
          (column) => columnsMap[column]?.return_period
        ),
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
    ...columns.map((column) => ({
      data: (val: TableDatum) => val[column] ?? null,
      title: column.replace(/_/g, " "),
      searchable: false,
    })),
  ];
  if (values_table) {
    values_table.destroy();
    jQuery("#values-table").empty();
  }
  const title = `Exposure at risk for ${countries.join(", ")} (${columns})`;

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
          ...createDataTableReferencesButtonArray(
            columns.map((col) => columnsMap[col]?.references ?? []).flat()
          ),
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
  const pinLabel = document
    .querySelector(`.pin-label-${slugify(key)}`)
    ?.textContent?.trim();
  const textTemplate = document
    .getElementById("table-datasets-list-item-template")!
    .innerHTML.replace(/\bCOLUMNKEY\b/g, key)!;
  const templateElement = document.createElement("template");
  templateElement.innerHTML = textTemplate;
  const pinLabelElement = templateElement.content.querySelector(".pin-label");
  if (pinLabelElement && pinLabel) {
    pinLabelElement.textContent = pinLabel;
  }
  toggleSelectArray(id, key, templateElement.content);
  updateTableButtonStates();
  window.formUpdate();
};

window.sortColumn = function sortColumn(key: string, direction: "up" | "down") {
  const id = "table-columns";
  reorderSelectArrayValues(id, key, direction);
  window.formUpdate();
};

async function getGeoJSON() {
  const params = getParamsGrouped();
  const countries = params.countries as Array<CountriesEnum | "ALL">;
  const areas = params.areas;
  const columns = params.table_columns;

  const data = await downloadGeoJSON({ countries, areas, columns });
  if (data) {
    createGeoJSONDownload(data, "myriad_exposure_at_risk.geojson");
  }
}

window.htmx.on("htmx:afterSwap", () => {
  updateTableButtonStates();
  updateMapButtonStates();
});

updateTableButtonStates();
updateMapButtonStates();
