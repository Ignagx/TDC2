# BOM – Placa 1 (TP2 TC2, actividad 2.1, Grupo 2)

Montaje THT en placa simple faz hecha por planchado. Los valores y las referencias salen del esquemático `placa.kicad_sch` (anotación del 31/10). Los pads de cocodrilo (H1, H2, H3) son cobre estañado y no se compran.

## Footprints

Son los oficiales de KiCad, salvo los dos que no tienen equivalente, que están en la biblioteca global `Rao`. Mechas: **0,8 mm** para casi todo, **1,0 mm** para cocodrilos y test points, y **1,2 mm** para C3.

| Footprint | Para | Pad | Mecha |
|---|---|---|---|
| `Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal` | Todas las R de ¼ W | redondo, 1,6 mm | 0,8 |
| `Package_DIP:DIP-14_W7.62mm_Socket` | U1, U2 (sobre zócalo) | redondo, 1,6 mm | 0,8 |
| `Package_TO_SOT_THT:TO-92_Inline_Wide` | Q1, Q2 (patas en línea a 2,54 mm) | 1,5 mm | 0,8 |
| `Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical` | RV1 | redondo, 1,44 mm | 0,8 |
| `Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm` | C1, C2 | redondo, 1,6 mm | 0,8 |
| `Capacitor_THT:C_Rect_L7.2mm_W5.5mm_P5.00mm_FKS2_FKP2_MKS2_MKP2` | C4 | redondo, 1,6 mm | 0,8 |
| `Capacitor_THT:C_Rect_L26.5mm_W10.5mm_P22.50mm_MKS4` | C3 | redondo, 2,4 mm | 1,2 |
| `Rao:Pad_Cocodrilo_6x8mm` | H1 (GND), H2 (+24V), H3 (VCTRL, generador) | rectangular, 6 × 8 mm | 1,0 |
| `Rao:TP_Puente_P5.08mm` | TP1 a TP6 (LAZO+, LAZO−, SALIDA1, SALIDA2, VE, VC) | dos redondos de 2,6 mm a 5,08 mm (alambre en U); los dos pads son un puente, así que no llevan pista entre ellos | 1,0 |

Los pads oficiales de 1,6 mm con mecha de 0,8 dejan un anillo de 0,4 mm: al planchar y perforar a mano conviene centrar bien la mecha. Si el poliéster que compren tiene otro paso, se cambia por otra variante `C_Rect_..._P7.50mm` o `P15.00mm` de `Capacitor_THT`.

## Semiconductores

| Cant. | Ref. | Componente | Tecnología / especificación | Encapsulado | Equivalentes y notas |
|---|---|---|---|---|---|
| 2 | U1, U2 | **LM324N** | Op-amp cuádruple bipolar, fuente simple de 3 a 32 V | DIP-14 | LM2902N (mismo pinout). La "N" final indica DIP. U1: fuente de prueba (U1B) y amplificador de instrumentación (U1A y U1C seguidores, U1D diferencial). U2: V → I (U2A) y Sallen-Key (U2D); U2B y U2C quedan libres, como seguidores a masa. |
| 2 | (U1, U2) | **Zócalo DIP-14** | Torneado (pines maquinados), de 0,3" (7,62 mm) | DIP-14 | Sirve uno común de lámina, pero el torneado hace mejor contacto. Footprint `DIP-14_W7.62mm_Socket`. |
| 2 | Q1, Q2 | **BC547B** (o BC337-25) | Transistor NPN de baja señal, 45 V / 100 mA / 500 mW | TO-92 | Q1: etapa 3 (V → I). Q2: fuente de corriente de prueba. Disipan como máximo 0,28 W a 20 mA: montarlos 2–3 mm separados de la placa. El footprint es **C-B-E** (BC547 y BC337 lo son; verificar con el medidor de hFE). ⚠️ El 2N2222A / PN2222A en TO-92 es **E-B-C**: si usan ese, se suelda girado 180°. |

## Resistencias

Todas son de **película metálica, ¼ W** (al 1 % donde se indica), con cuerpo de 6,3 mm y paso de 10,16 mm (footprint `R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal`). En Córdoba se venden al 1 % en valores E24 (8K2, 15K, etc.).

| Cant. | Ref. | Valor | Función | Notas |
|---|---|---|---|---|
| 4 | R16, R17, R18, R19 | **10 kΩ 1 %** | Amplificador diferencial (etapa 1) | De estas cuatro depende el rechazo de modo común. Conviene comprar 5 o 6 y elegir con el multímetro las 4 más parecidas. |
| 1 | R20 | **8,2 kΩ 1 %** (8K2) | Filtro Sallen-Key | 8K2 está en E24 (no en E96), pero al 1 % se consigue. |
| 1 | R21 | **15 kΩ 1 %** | Filtro Sallen-Key | |
| 4 | R6, R8, R9, R14 | **100 Ω 1 %** | Ver la tabla de abajo | |
| 4 | R7, R10, R11, R13 | **150 Ω 1 %** | Ver la tabla de abajo | Una de 150 disipa como máximo 60 mW, así que ¼ W alcanza. |
| 3 | R1, R5, R12 | **1 kΩ** | R5 y R12: RB de Q1 y Q2. R1: parte baja del divisor de Vctrl | Pueden ser al 5 %. |
| 1 | R2 | **22 kΩ** | Parte alta del divisor de Vctrl (desde +24 V) | Al 5 %. Con R1 y RV1 de 10k, Vctrl va de 0,73 a 8 V (2,9 a 32 mA). Con 39 kΩ quedaría en 0,48–5,28 V. |
| 2 | R3, R4 | **10 kΩ** | R3: del cursor de RV1 a VCTRL. R4: protección de la entrada + de U1B | Al 5 %. |
| 1 | R15 | **1 MΩ** | R_CM | Puede ser al 5 %. |

Las resistencias de 100 y 150 Ω forman cuatro valores en serie:

| Combinación | Total | Función |
|---|---|---|
| R14 + R13 | 250 Ω | Rshunt de entrada |
| R9 + R10 | 250 Ω | Rshunt de salida (emisor) |
| R8 + R7 | 250 Ω | Rcarga (colector) |
| R6 + R11 | 250 Ω | Rs de la fuente de prueba: I = Vctrl / Rs |

## Potenciómetro

| Cant. | Ref. | Valor | Tecnología | Encapsulado | Notas |
|---|---|---|---|---|---|
| 1 | RV1 | **10 kΩ** (código "103") | Preset multivuelta de cermet, 25 vueltas | **3296W** (vertical, ajuste desde arriba) | Divisor de Vctrl para el ensayo estático (entre R2 y R1). El diseño original era de 5 kΩ (0,86–5,14 V). Con 10 kΩ se puede pasar de 20 mA: ajustar midiendo para no superar 5 V de Vctrl. |

## Capacitores

| Cant. | Ref. | Valor | Tecnología | Paso en el footprint | Notas |
|---|---|---|---|---|---|
| 1 | C4 | **1 µF** | **Poliéster metalizado (MKT)**, ≥ 63 V (100 V es lo común), tolerancia J (±5 %) o K (±10 %) | 5 o 7,5 mm | Filtro: la consigna pide **poliéster o film, no electrolítico**. ⚠️ Los que compraron dicen "1nJ100": son de **1 nF**, no sirven. Hay que buscar uno marcado "1µ", "1u0" o "105". Ojo: "µ1" o "104" es 100 nF. |
| 1 | C3 | **2,2 µF** | Poliéster metalizado (MKT), ≥ 63 V, J o K | 22,5 mm | ✅ Comprado: EPCOS B32523, marcado "2U2 K 250" (±10 %, 250 V). Cuerpo de 26,5 × 10,5 × 16,5 mm. |
| 2 | C1, C2 | **100 nF** (código "104") | Cerámico multicapa (MLCC, X7R) o disco cerámico, 50 V | 5 mm | Desacople: C1 para U1 y C2 para U2, cada uno pegado al pin 4 (+24 V) de su integrado. |

> ⚠️ **Antes de imprimir el PCB, medí el paso y el tamaño de los poliéster que compres** y ajustá el footprint de C3 y C4. Cambian mucho según la marca. Si tenés acceso a un capacímetro o LCR, medí el valor real de C3 y C4: sirve para recalcular la fc en el paso 7.

## Fabricación y consumibles (no están en el esquemático)

| Cant. | Ítem | Especificación |
|---|---|---|
| 1 | Placa virgen | Simple faz, **FR4 (fibra de vidrio)**, 1,6 mm, cobre de 35 µm. Unos 10 × 10 cm; el tamaño final sale del layout. El FR4 aguanta mejor que el pertinax el calor y los cocodrilos sobre los pads. |
| – | Ataque químico | Percloruro férrico; transferencia por tóner (planchado). |
| – | Mechas | 0,8 mm (resistencias, CI, TO-92, 3296W, C1, C2 y C4), 1,0 mm (pads de cocodrilo y test points) y 1,2 mm (C3). |
| – | Estaño | 60/40 o 63/37, de 0,8 mm. |

## Test points

Para medir corrientes sin amperímetro (multímetro en volts de continua): **Iin = V(TP2) / 250 Ω** (caída en Rs) o **(V(TP1) − V(TP2)) / 250 Ω** (caída en el shunt de entrada). La corriente que va al PLC es la de colector: **Iout = (V(H2) − V(TP6)) / 250 Ω** (caída en Rcarga, multímetro entre H2 y TP6). **V(TP5) / 250 Ω** es la corriente de emisor (Ie = Iout / α, entre 0,2 y 0,5 % mayor con un BC547B); se usa en el ensayo dinámico porque está referida a GND y se puede medir con el osciloscopio.

TP1 a TP6 no se compran: son un alambre rígido (por ejemplo, una pata cortada de resistencia) doblado en U y soldado entre los dos agujeros, para enganchar la punta del osciloscopio o un cocodrilo.

## Repuestos sugeridos

1 LM324N, 1 BC547B y una o dos resistencias de más de cada valor al 1 %. Son baratos y evitan volver al local si algo se rompe al soldar.

## Dónde comprar en Córdoba

La zona de casas de electrónica está sobre **Rivera Indarte, entre Santa Rosa y La Rioja**. Antes de ir, conviene llamar y confirmar que tengan stock de LM324N, BC547B (o BC337-25), el preset 3296W y los poliéster de 1 µF y 2,2 µF.
