import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = path.resolve("..", "outputs", "datos_prueba");
const outputPath = path.join(outputDir, "movimientos_oracle_prueba_10k.xlsx");

const ROW_COUNT = 10000;

const headers = [
  "FECHA_TRANSACCION",
  "NUMERO_TRANSACCION",
  "ARTICULO",
  "DESCRIPCION",
  "CANTIDAD",
  "UNIDAD_MEDIDA",
  "SUBINVENTARIO",
  "ORG ORIGEN",
  "ORG DESTINO",
  "TIPO TRANSACCION",
  "TIPO ORIGEN",
  "ORIGEN",
  "MOTIVO",
  "LOTE",
  "USUARIO",
];

const internas = [
  "16_FARMA_FARMACIA_INTERNA_CRS",
  "47_FARMA_ALMACEN_CIRUGIA_CRS",
  "256_FARMA_URGENCIAS_CRS",
];
const cedis = [
  "1058_CRUZ_VERDE_CEDI_COTA_ALMACEN_PRINCIPAL",
  "337_FARMA_NO_VENDIBLE",
  "901_CRUZ_VERDE_ALMACEN_DE_AVERIADOS",
  "991_CRUZ_VERDE_PICKING_DEVOLUCIONES",
];
const externas = [
  "104_FARMA_CENTRAL_PREP_BOG",
  "1368_CRUZ_VERDE_CONSUMO_CUC_FIH",
  "1557_CRUZ_VERDE_FIH_CLINICA_EIREN",
  "20_FARMA_CLINICA_COUNTRY",
  "228_FARMA_FARMACIA_INTERNA_CUC",
  "255_FARMA_ALMACEN_CIRUGIA_CUC",
  "315_CRUZ_VERDE_CANCEROLOGICO",
  "480_VIRTUAL_FACTURACION_CLIENTE_EXTERNO",
  "919_CRUZ_VERDE_FARMACIA_EDIFICIO_BLUE",
];
const mceCodes = [
  "21817", "71837", "73796", "383679", "386588", "162397", "390482", "388907",
  "109046", "548339", "555234", "109491", "393397", "60744", "388908", "37785",
  "561531", "534011", "106876", "169534", "167725", "123778", "106877", "135679",
  "525052", "137151", "384851",
];
const liquidosCodes = [
  "63192", "19891", "388835", "19929", "388839", "388828", "388832",
  "19949", "100479", "19967", "140663", "388840", "32219", "388856",
];
const generales = [
  "A1001", "A1002", "A1003", "B2201", "C3301", "D4401", "E5501", "F6601",
  "G7701", "H8801", "I9901", "J1101",
];

const descriptions = new Map([
  ...mceCodes.map((code, index) => [code, `Insumo MCE cirugia ${String(index + 1).padStart(2, "0")}`]),
  ...liquidosCodes.map((code, index) => [code, `Liquido cirugia ${String(index + 1).padStart(2, "0")}`]),
  ...generales.map((code, index) => [code, `Medicamento general prueba ${String(index + 1).padStart(2, "0")}`]),
]);

function rng(seed = 424242) {
  let state = seed >>> 0;
  return () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 2 ** 32;
  };
}
const random = rng();

function pick(items) {
  return items[Math.floor(random() * items.length)];
}

function dateFor(index) {
  const date = new Date(Date.UTC(2026, 0, 1 + (index % 120)));
  return date.toISOString().slice(0, 10);
}

function qty(sign = 1) {
  return sign * (1 + Math.floor(random() * 24));
}

function article(pool = generales) {
  const code = pick(pool);
  return [code, descriptions.get(code) ?? `Articulo ${code}`];
}

const templates = [
  ["DISPENSACION_AL_PACIENTE", 850, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(-1), "UND", "FARMACIA", "", pick(internas), "Sales order issue", "Sales order", "PACIENTE", ""];
  }],
  ["DISPENSACION_CONSUMO", 760, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(-1), "UND", "FARMACIA", "", "16_FARMA_FARMACIA_INTERNA_CRS", "Sales order issue", "Sales order", "CONSUMO", ""];
  }],
  ["DISPENSACION_AL_PACIENTE_MCE", 620, () => {
    const [code, desc] = article(mceCodes);
    return [code, desc, qty(-1), "UND", "CIRUGIA", "", "47_FARMA_ALMACEN_CIRUGIA_CRS", "Sales order issue", "Sales order", "PACIENTE", ""];
  }],
  ["LIQUIDOS_CIRUGIA", 520, () => {
    const [code, desc] = article(liquidosCodes);
    return [code, desc, qty(-1), "UND", "CIRUGIA", "", "47_FARMA_ALMACEN_CIRUGIA_CRS", "Sales order issue", "Sales order", "PACIENTE", ""];
  }],
  ["DEVOLUCIONES", 560, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(1), "UND", "FARMACIA", pick(externas), pick(internas), "RMA Receipt", "RMA", "DEVOLUCION", ""];
  }],
  ["ENTRADAS_PRESTAMOS_INTERNOS", 650, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(1), "UND", "FARMACIA", pick(internas), pick(internas), "Intransit Receipt", "Inventory", "TRASLADO INTERNO", ""];
  }],
  ["ENTRADAS_MCE", 520, () => {
    const [code, desc] = article(mceCodes);
    return [code, desc, qty(1), "UND", "CIRUGIA", "16_FARMA_FARMACIA_INTERNA_CRS", "47_FARMA_ALMACEN_CIRUGIA_CRS", "Intransit Receipt", "Inventory", "TRASLADO INTERNO", ""];
  }],
  ["ALISTAMIENTO_PYXIS", 460, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(1), "UND", "PYXIS_URGE", "16_FARMA_FARMACIA_INTERNA_CRS", "256_FARMA_URGENCIAS_CRS", "Intransit Receipt", "Inventory", "TRASLADO INTERNO", ""];
  }],
  ["SALIDAS_PRESTAMOS_INTERNOS", 520, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(-1), "UND", "FARMACIA", pick(internas), pick(internas), "Intransit Shipment", "Inventory", "TRASLADO INTERNO", ""];
  }],
  ["SALIDAS_PRESTAMOS_EXTERNOS", 540, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(-1), "UND", "FARMACIA", pick(externas), pick(internas), "Intransit Shipment", "Inventory", "PRESTAMO EXTERNO", ""];
  }],
  ["ENTRADAS_CEDI", 560, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(1), "UND", "FARMACIA", pick(cedis), pick(["16_FARMA_FARMACIA_INTERNA_CRS", "47_FARMA_ALMACEN_CIRUGIA_CRS"]), "Account alias receipt", "Account alias", "RECEPCION CEDI", ""];
  }],
  ["ENTRADAS_CENTRAL_PREP", 470, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(1), "UND", "CENTRAL_PREP", "104_FARMA_CENTRAL_PREP_BOG", pick(["16_FARMA_FARMACIA_INTERNA_CRS", "47_FARMA_ALMACEN_CIRUGIA_CRS"]), pick(["Int Req Intr Rcpt", "Intransit Receipt"]), pick(["Internal requisition", "Inventory"]), "CENTRAL PREP", ""];
  }],
  ["ENTRADAS_CENTRAL_PREP_UNIDOSIS", 430, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(1), "UND", "UNIDOSIS", "104_FARMA_CENTRAL_PREP_BOG", pick(["16_FARMA_FARMACIA_INTERNA_CRS", "47_FARMA_ALMACEN_CIRUGIA_CRS"]), pick(["Int Req Intr Rcpt", "Intransit Receipt"]), pick(["Internal requisition", "Inventory"]), "CENTRAL PREP", ""];
  }],
  ["ORDENES_DE_COMPRA", 430, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(1), "UND", "FARMACIA", "PROVEEDOR_ORACLE", pick(["16_FARMA_FARMACIA_INTERNA_CRS", "47_FARMA_ALMACEN_CIRUGIA_CRS"]), "PO Receipt", "Purchase order", "ORDEN COMPRA", ""];
  }],
  ["PRESTAMOS_BOPOS", 430, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(1), "UND", "FARMACIA", "BOPOS_ORIGEN", "16_FARMA_FARMACIA_INTERNA_CRS", pick(["Account alias receipt", "Account alias issue"]), "Account alias", "MOVIMIENTOS BOPOS-EBS", ""];
  }],
  ["AJUSTES_BASE_CAPTURA", 430, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(-1), "UND", "FARMACIA", "", pick(internas), "Account alias issue", "Account alias", pick(["AA PRODUCTOS AVERIADOS DE PUNTOS", "AA PROXIMOS A VENCER DE PUNTOS", "ANEXO 6 SALIDA DESTRUCCION MCE"]), "AJUSTE"];
  }],
  ["AJUSTES_INCONSISTENCIAS", 390, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(1), "UND", "FARMACIA", "", pick(["16_FARMA_FARMACIA_INTERNA_CRS", "47_FARMA_ALMACEN_CIRUGIA_CRS"]), pick(["Account alias issue", "Account alias receipt"]), "Account alias", pick(["LEGALIZACION INCONSIST DEVOLUCIONES PTO", "LEGALIZACION INCONSISTENCIAS DESPACHO"]), "AJUSTE"];
  }],
  ["OTROS_AJUSTES", 410, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(1), "UND", "FARMACIA", "", pick(internas), pick(["Account alias issue", "Account alias receipt"]), "Account alias", "OTRO AJUSTE OPERATIVO", "AJUSTE"];
  }],
  ["EFECTO_CERO", 390, () => {
    const [code, desc] = article(generales);
    return [code, desc, 0, "UND", "FARMACIA", "", pick(internas), pick(["Subinventory Transfer", "Internal Order Pick"]), pick(["Inventory", "Internal order"]), "EFECTO CERO", ""];
  }],
  ["CONTEO_CICLICO", 300, () => {
    const [code, desc] = article(generales);
    return [code, desc, qty(1), "UND", "FARMACIA", "", pick(internas), "Cycle Count Adjust", "Cycle Count", "CONTEO", ""];
  }],
  ["SIN_CLASIFICAR", 590, () => {
    const [code, desc] = article([...generales, ...mceCodes, ...liquidosCodes]);
    return [code, desc, qty(1), "UND", "SIN_MAPEO", "999_ORG_DESCONOCIDA", "888_FARMACIA_NUEVA_NO_MAPEADA", "Misc Transaction", "Manual", "PRUEBA SIN REGLA", "REVISION"];
  }],
];

const expanded = [];
for (const [name, count, factory] of templates) {
  for (let i = 0; i < count; i += 1) {
    expanded.push([name, factory]);
  }
}
while (expanded.length < ROW_COUNT) {
  expanded.push(["DISPENSACION_AL_PACIENTE", templates[0][2]]);
}

for (let i = expanded.length - 1; i > 0; i -= 1) {
  const j = Math.floor(random() * (i + 1));
  [expanded[i], expanded[j]] = [expanded[j], expanded[i]];
}

const rows = [headers];
const expectedCounts = new Map();
for (let i = 0; i < ROW_COUNT; i += 1) {
  const [expected, factory] = expanded[i];
  expectedCounts.set(expected, (expectedCounts.get(expected) ?? 0) + 1);
  const [code, desc, cantidad, unidad, subinventario, orgOrigen, orgDestino, tipoTransaccion, tipoOrigen, origen, motivo] = factory();
  rows.push([
    dateFor(i),
    `TX-${String(i + 1).padStart(6, "0")}`,
    code,
    desc,
    cantidad,
    unidad,
    subinventario,
    orgOrigen,
    orgDestino,
    tipoTransaccion,
    tipoOrigen,
    origen,
    motivo,
    `L-${String(1000 + (i % 250)).padStart(4, "0")}`,
    `usuario_${1 + (i % 12)}`,
  ]);
}

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Movimientos");
sheet.getRangeByIndexes(0, 0, rows.length, headers.length).values = rows;
sheet.freezePanes.freezeRows(1);
sheet.showGridLines = false;

sheet.getRangeByIndexes(0, 0, 1, headers.length).format = {
  fill: "#1F4E78",
  font: { bold: true, color: "#FFFFFF" },
  wrapText: true,
};
sheet.getRangeByIndexes(1, 4, ROW_COUNT, 1).format.numberFormat = "0";
sheet.getRangeByIndexes(1, 0, ROW_COUNT, 1).format.numberFormat = "yyyy-mm-dd";
const widths = [120, 135, 90, 230, 85, 95, 120, 280, 280, 165, 145, 210, 130, 90, 100];
widths.forEach((width, index) => {
  sheet.getRangeByIndexes(0, index, ROW_COUNT + 1, 1).format.columnWidthPx = width;
});
sheet.tables.add(`A1:O${ROW_COUNT + 1}`, true, "MovimientosOraclePrueba");

const guide = workbook.worksheets.add("Guia_Prueba");
const summaryRows = [
  ["Archivo de prueba", "Movimientos Oracle 10k"],
  ["Filas en Movimientos", ROW_COUNT],
  ["Hoja para cargar en la app", "Movimientos"],
  ["Notas", "Incluye reglas base, reglas derivadas, articulos MCE, liquidos cirugia, farmacias internas ORG DESTINO y registros sin clasificar."],
  [],
  ["TIPOLOGIA_OBJETIVO", "FILAS_GENERADAS"],
  ...[...expectedCounts.entries()].sort((a, b) => a[0].localeCompare(b[0])),
];
guide.getRangeByIndexes(0, 0, summaryRows.length, 2).values = summaryRows;
guide.getRange("A1:B1").format = { fill: "#1F4E78", font: { bold: true, color: "#FFFFFF" } };
guide.getRange("A6:B6").format = { fill: "#D9EAF7", font: { bold: true, color: "#0B3F66" } };
guide.getRange("A:A").format.columnWidthPx = 250;
guide.getRange("B:B").format.columnWidthPx = 180;
guide.freezePanes.freezeRows(6);
guide.showGridLines = false;

await fs.mkdir(outputDir, { recursive: true });
const preview = await workbook.render({ sheetName: "Movimientos", range: "A1:O25", scale: 1, format: "png" });
await fs.writeFile(path.join(outputDir, "preview_movimientos_10k.png"), new Uint8Array(await preview.arrayBuffer()));
const check = await workbook.inspect({
  kind: "table",
  range: "Movimientos!A1:O12",
  include: "values",
  tableMaxRows: 12,
  tableMaxCols: 15,
});
console.log(check.ndjson);
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
