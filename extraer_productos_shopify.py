from dotenv import load_dotenv
load_dotenv()
import os
import json
import csv
import re
import urllib.request
from pathlib import Path

SHOP_URL = "libreriatroya-com.myshopify.com"
API_TOKEN = os.getenv("SHOPIFY_API_TOKEN")
API_VERSION = "2024-04"
GRAPHQL_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}/graphql.json"
STORE_FRONTEND_URL = "https://libreriatroya.com"

RAW_DATA_1 = """
1,9789974894181,La zorra y la cigüeña 3D,N/A,,5.00,"$36,500.00",0.00%,$0.00,"$109,500.00",
2,9789974679115,Mitos y leyendas de américa latina,N/A,,5.00,"$38,000.00",0.00%,$0.00,"$114,000.00",
3,9789974894174,La cigarra y la hormiga 3D,N/A,,5.00,"$36,500.00",0.00%,$0.00,"$109,500.00",
4,9789915662022,Mimitos animales,N/A,,5.00,"$39,000.00",0.00%,$0.00,"$117,000.00",
5,9789915662015,Mimitos colores,N/A,,5.00,"$39,000.00",0.00%,$0.00,"$117,000.00",
6,9789915662039,Mimitos frutas,N/A,,5.00,"$39,000.00",0.00%,$0.00,"$117,000.00",
7,9789974702479,Mis cuentos clásicos en 3D Blancanieves,N/A,,5.00,"$22,000.00",0.00%,$0.00,"$66,000.00",
8,9789974885912,La sirenita mis cuentos clásicos en 3D,N/A,,5.00,"$22,000.00",0.00%,$0.00,"$66,000.00",
9,9789974702509,Pinocho mis cuentos clásicos en 3D,N/A,,5.00,"$22,000.00",0.00%,$0.00,"$66,000.00",
10,9789974702684,Mis cuentos clasicos en 3d Bambi,N/A,,15.00,"$22,000.00",0.00%,$0.00,"$198,000.00",
11,9789974697324,Mis cuentos clásicos la bella durmiente en 3D,N/A,,5.00,"$22,000.00",0.00%,$0.00,"$66,000.00",
12,9789974885905,Mis cuentos clásicos en 3D El patito feo,N/A,,5.00,"$22,000.00",0.00%,$0.00,"$66,000.00",
13,9789974885929,Mis cuentos clásicos en 3D Peter Pan,N/A,,5.00,"$22,000.00",0.00%,$0.00,"$66,000.00",
14,9789974697331,Cenicienta mis cuentos clásicos en 3D,N/A,,5.00,"$22,000.00",0.00%,$0.00,"$66,000.00",
15,9789974702691,Mis cuentos clásicos en 3d El gato con botas,N/A,,5.00,"$22,000.00",0.00%,$0.00,"$66,000.00",
16,9789974885899,El mago de oz mis cuentos clásicos en 3D,N/A,,5.00,"$22,000.00",0.00%,$0.00,"$66,000.00",
17,9789915662060,Mimitos primeras palabras,N/A,,5.00,"$39,000.00",0.00%,$0.00,"$117,000.00",
18,9789974894167,El pastor embustero 3D,N/A,,5.00,"$36,500.00",0.00%,$0.00,"$109,500.00",
19,9789974744646,Canción de navidad. Novela gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
20,9789974697676,Alicia en el país de las maravillas. Novela gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
21,9789871208630,Alí Baba y los 40 ladrones. Novela gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
22,9789871208838,Aladino y la lámpara mágica. Novela gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
23,9789974679979,El extraño caso del doctor Jekyll y Mr Hyde. Novela Gráfica,N/A,,5.00,"$31,000.00",0.00%,$0.00,"$93,000.00",
24,9789974684058,Drácula. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
25,9789974690370,El hombre invisible. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
26,9789871208814,El jorobado de norte dame. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
27,1000009170,El libro de la selva. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
28,9789974697652,El mago de Oz,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
29,9789871208623,El rey arturo y los caballeros de la mesa redonda. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
30,9789974679962,El Sabueso de los baskerville. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
31,9789974690349,Frankenstein. Novela Gráfica,N/A,,5.00,"$31,000.00",0.00%,$0.00,"$93,000.00",
32,9789974690929,Jasón y los argonautas. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
33,9789974690356,La familia Robinson,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
34,9789974679986,La guerra de los mundos novela gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
35,9789871208821,La isla del cesoro. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
36,9789974690363,La leyenda del jinete sin cabeza. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
37,9789974684072,La maquina del tiempo,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
38,9789974697669,Los siete viajes de Simbad. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
39,9789974690936,Los trabajos de hércules,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
40,9789974684065,Los viajes de Gulliver. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
41,9789974690943,Perseo y medusa. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
42,9789974744653,Peter Pan. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
43,9789871208807,Pinocho. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
44,9789974684041,Robin Hood. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
45,9789974690950,Teseo y el minotauro. Novela Gráfica,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
46,9789974702066,Ana Frank. Novela Gráfica,N/A,,5.00,"$35,000.00",0.00%,$0.00,"$105,000.00",
47,9789974679993,20.000 Leguas de viaje submarino,N/A,,3.00,"$31,000.00",0.00%,$0.00,"$55,800.00",
48,9789974885349,Leonardo da vinci. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
49,1000011984,Mandela. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
50,9789871208470,Cantar de mío cid. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
51,9789871208951,El corazón de las tinieblas,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
52,9789874108159,El conde de Montecristo. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
53,9789974894921,El fantasma de la ópera. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
54,9789871208968,El mundo perdido. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
55,1000004440,El retrato de dorian gray. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
56,9789871208944,Ivanhoe. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
57,9789974894914,La Eneida. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
58,9789871208586,La Ilíada. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
59,9789871208975,La isla del doctor Moreau. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
60,9789874108166,La vuelta al mundo en 80 días. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
61,9789871208463,Los 3 mosqueteros. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
62,9789871208593,Los Miserables. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
63,9789871208869,Moby dick,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
64,9789871208845,Narración de Arthur Gordon pym. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
65,9789871208852,Robinson Crusoe. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
66,9789974702073,Romeo y Julieta. Novela Gráfica,N/A,,3.00,"$35,000.00",0.00%,$0.00,"$63,000.00",
67,9789974728400,Origami fácil,N/A,,5.00,"$36,000.00",0.00%,$0.00,"$108,000.00",
68,9789974744608,Amigos en el mar puzzle aventuras,N/A,,5.00,"$29,000.00",0.00%,$0.00,"$87,000.00",
69,9789974744615,Puzzle aventuras la fiesta de las aves,N/A,,5.00,"$29,000.00",0.00%,$0.00,"$87,000.00",
70,9789974744622,La granja despierta,N/A,,5.00,"$29,000.00",0.00%,$0.00,"$87,000.00",
71,9789915670331,¿Quién soy textura?. En la ciudad,N/A,,5.00,"$48,000.00",0.00%,$0.00,"$144,000.00",
72,9789915670317,¿Quién soy textura? En la granja,N/A,,5.00,"$48,000.00",0.00%,$0.00,"$144,000.00",
73,9789915670348,¿Quién soy textura? En la jungla,N/A,,5.00,"$48,000.00",0.00%,$0.00,"$144,000.00",
74,9789915670324,¿Quién soy textura? En el océano,N/A,,5.00,"$48,000.00",0.00%,$0.00,"$144,000.00",
75,9789974885936,El pinguino perdido,N/A,,5.00,"$38,000.00",0.00%,$0.00,"$114,000.00",
76,9789974885943,La mejor mamá de todas,N/A,,5.00,"$38,000.00",0.00%,$0.00,"$114,000.00",
77,9789974885950,Los amo más,N/A,,5.00,"$38,000.00",0.00%,$0.00,"$114,000.00",
78,9789974744165,Solo tu y yo,N/A,,5.00,"$38,000.00",0.00%,$0.00,"$114,000.00",
79,9789974744172,Un abrazo más,N/A,,5.00,"$38,000.00",0.00%,$0.00,"$114,000.00",
80,9789915686011,Mi asombroso libro del océano,N/A,,5.00,"$28,000.00",0.00%,$0.00,"$84,000.00",
81,9789915670980,Suavecines dinosaurios,N/A,,5.00,"$34,000.00",0.00%,$0.00,"$102,000.00",
82,9789915677002,Suavecines domésticos,N/A,,5.00,"$34,000.00",0.00%,$0.00,"$102,000.00",
83,9789915670997,Suavecines marinos,N/A,,5.00,"$34,000.00",0.00%,$0.00,"$102,000.00",
84,9789915677019,Suavecines silvestres,N/A,,5.00,"$34,000.00",0.00%,$0.00,"$102,000.00",
85,9789974904903,Diversión en el hogar,N/A,,5.00,"$20,000.00",0.00%,$0.00,"$60,000.00",
86,9789974904910,Diversión en el océano,N/A,,5.00,"$20,000.00",0.00%,$0.00,"$60,000.00",
87,9789974904934,Diversión en la jungla,N/A,,5.00,"$20,000.00",0.00%,$0.00,"$60,000.00",
88,9789915651132,Suave texturas en el corazón de la jungla,N/A,,5.00,"$49,500.00",0.00%,$0.00,"$148,500.00",
89,9789915651316,Suaves texturas En el mundo miniatura,N/A,,5.00,"$49,500.00",0.00%,$0.00,"$148,500.00",
90,9789915651156,Suave texturas en la tierra prehistórica,N/A,,5.00,"$49,500.00",0.00%,$0.00,"$148,500.00",
91,9789915651163,Suave texturas en lo profundo del océano,N/A,,5.00,"$49,500.00",0.00%,$0.00,"$148,500.00",
92,9789974697867,Viajes fantásticos aventura submarina en 3D,N/A,,5.00,"$45,000.00",0.00%,$0.00,"$135,000.00",
93,9789974904095,Ya soy grande cirilo come de todo,N/A,,5.00,"$22,500.00",0.00%,$0.00,"$67,500.00",
94,9789974904101,Ya soy grande federico cepilla sus dientes,N/A,,5.00,"$22,500.00",0.00%,$0.00,"$67,500.00",
95,9789974904118,Ya soy grande lito aprende a compartir,N/A,,5.00,"$22,500.00",0.00%,$0.00,"$67,500.00",
96,9789974904125,Ya soy grande ludovico disfruta del baño,N/A,,5.00,"$22,500.00",0.00%,$0.00,"$67,500.00",
97,9789974904132,Ya soy grande Marcelino duerme solo,N/A,,5.00,"$22,500.00",0.00%,$0.00,"$67,500.00",
98,9789974904149,Ya soy grande pipo deja el chupete,N/A,,5.00,"$22,500.00",0.00%,$0.00,"$67,500.00",
99,9789974904156,Ya soy grande serafín deja el biberón,N/A,,5.00,"$22,500.00",0.00%,$0.00,"$67,500.00",
100,9789974904163,Ya soy grande tito no usa pañal,N/A,,5.00,"$22,500.00",0.00%,$0.00,"$67,500.00",
101,7751035000802,Caligrafía coquito 360 ejercicios 6 cuadernos a todo color,N/A,,5.00,"$39,000.00",0.00%,$0.00,"$117,000.00",
102,9786125051400,Coquito auténtico,N/A,,5.00,"$11,900.00",0.00%,$0.00,"$35,700.00",
103,9786124000829,Coquito clásico,N/A,,5.00,"$17,900.00",0.00%,$0.00,"$53,700.00",
104,9786125051509,Coquito oro,N/A,,5.00,"$39,000.00",0.00%,$0.00,"$117,000.00",
105,9786125051813,Coquito iniciación en la lectura,N/A,,5.00,"$11,900.00",0.00%,$0.00,"$35,700.00",
106,9789915682457,¡Le gano a los miedos! no hablo con extraños,N/A,,5.00,"$28,000.00",0.00%,$0.00,"$84,000.00",
107,9789915682440,¡Le gano a los miedos! no temo a la oscuridad,N/A,,5.00,"$28,000.00",0.00%,$0.00,"$84,000.00",
108,9789915682433,!Le gano a los miedos¡ qué hago si me pierdo,N/A,,5.00,"$28,000.00",0.00%,$0.00,"$84,000.00",
109,9789974744929,365 Actividades divertidas. Naranja,N/A,,5.00,"$28,000.00",0.00%,$0.00,"$84,000.00",
110,9789974744936,365 Actividades fabulosas. Amarilla,N/A,,5.00,"$28,000.00",0.00%,$0.00,"$84,000.00",
111,9789915680408,365 Escenas para colorear,N/A,,5.00,"$28,000.00",0.00%,$0.00,"$84,000.00",
112,9789974744943,365 Motivos para colorear. Rosa,N/A,,5.00,"$28,000.00",0.00%,$0.00,"$84,000.00",
113,9789974728592,Animalitos es hora de bañarse,N/A,,5.00,"$25,000.00",0.00%,$0.00,"$75,000.00",
114,9789974728608,Animalitos La comida de mamá,N/A,,5.00,"$25,000.00",0.00%,$0.00,"$75,000.00",
115,9789974728844,Pedro y los colores,N/A,,5.00,"$29,000.00",0.00%,$0.00,"$87,000.00",
116,9789974728615,Animalitos todo en orden,N/A,,5.00,"$25,000.00",0.00%,$0.00,"$75,000.00",
117,9789974728622,Animalitos una sonrisa reluciente,N/A,,5.00,"$25,000.00",0.00%,$0.00,"$75,000.00",
118,9789974738416,Océano colección botecitos aqualibros,N/A,,5.00,"$39,000.00",0.00%,$0.00,"$117,000.00",
119,9789974738423,La granja colección botecitos aqualibros,N/A,,5.00,"$39,000.00",0.00%,$0.00,"$117,000.00",
120,9789974738430,La jungla colección botecitos aqualibros,N/A,,5.00,"$39,000.00",0.00%,$0.00,"$117,000.00",
121,9789974738447,Mascotas colección botecitos aqualibros,N/A,,5.00,"$39,000.00",0.00%,$0.00,"$117,000.00",
122,9789974738935,Atlas visual del cuerpo humano,N/A,,5.00,"$58,000.00",0.00%,$0.00,"$174,000.00",
123,9789974679672,Atlas visual del reino animal,N/A,,5.00,"$58,000.00",0.00%,$0.00,"$174,000.00",
124,9789974679689,Atlas visual del reino vegetal,N/A,,5.00,"$58,000.00",0.00%,$0.00,"$174,000.00",
125,9789915677743,¡Adiós pañal!,N/A,,3.00,"$55,000.00",0.00%,$0.00,"$99,000.00",
126,9789974885165,Cuentos para 2 años los mejores cuentos para niños y niñas,N/A,,3.00,"$34,000.00",0.00%,$0.00,"$61,200.00",
127,9789974885172,cuentos para 3 años los mejores cuentos para niños y niñas,N/A,,3.00,"$34,000.00",0.00%,$0.00,"$61,200.00",
128,9789974717053,Dibujo y descubro formas,N/A,,5.00,"$42,500.00",0.00%,$0.00,"$127,500.00",
129,9789974728103,Dinosaurios gigantes y acorazados en 3D,N/A,,5.00,"$29,000.00",0.00%,$0.00,"$87,000.00",
130,9789974728080,Dinosaurios choque de titanes en 3D,N/A,,5.00,"$29,000.00",0.00%,$0.00,"$87,000.00",
131,9789974728097,Dinosaurios grandes cazadores 3D,N/A,,5.00,"$29,000.00",0.00%,$0.00,"$87,000.00",
132,9789974728110,Dinosaurios Pop Up 3D Los Más Feroces,N/A,,5.00,"$29,000.00",0.00%,$0.00,"$87,000.00",
133,9789915670249,Te amo mami,N/A,,5.00,"$38,000.00",0.00%,$0.00,"$114,000.00",
134,9789915670232,Te amo papi,N/A,,5.00,"$38,000.00",0.00%,$0.00,"$114,000.00",
135,9789974904248,Mis primeras historias dela biblia,N/A,,5.00,"$38,000.00",0.00%,$0.00,"$114,000.00",
136,9789974744141,Deseos a las estrellas,N/A,,5.00,"$39,500.00",0.00%,$0.00,"$118,500.00",
137,9789871208647,Viaje al centro de la tierra. Novela gráfica,N/A,,5.00,"$31,000.00",0.00%,$0.00,"$93,000.00",
138,9789974702486,Mis cuentos clásicos en 3d Caperucita roja,N/A,,5.00,"$22,000.00",0.00%,$0.00,"$66,000.00",
139,9789974894198,La liebre y la tortuga 3D,N/A,,5.00,"$36,500.00",0.00%,$0.00,"$109,500.00",
"""

RAW_DATA_2 = """
1,9789580807575,Los 10 limites del humor,N/A,,4.00,"$59,900.00",0.00%,$0.00,"$155,740.00",
2,9789580807612,Una cátedra en Colombia,N/A,,4.00,"$59,900.00",0.00%,$0.00,"$155,740.00",
"""

RAW_DATA_3 = """
1,9788416994588,Innovación interior,N/A,,2.00,"$144,900.00",0.00%,$0.00,"$188,370.00",
2,9788416994243,El santuario de la tierra,N/A,,2.00,"$161,000.00",0.00%,$0.00,"$209,300.00",
3,9788416994908,El códice mexica,N/A,,2.00,"$153,000.00",0.00%,$0.00,"$198,900.00",
4,9788417566982,El arcángel metatrón,N/A,,2.00,"$144,900.00",0.00%,$0.00,"$188,370.00",
5,9788416364411,Relatos de la otra realidad,N/A,,2.00,"$136,900.00",0.00%,$0.00,"$177,970.00",
6,9788418263057,La muerte no existe,N/A,,2.00,"$128,800.00",0.00%,$0.00,"$167,440.00",
7,9788416364435,La muerte y el duelo a través de los cuentos,N/A,,2.00,"$144,900.00",0.00%,$0.00,"$188,370.00",
8,9788416364671,El escarabajo rojo,N/A,,2.00,"$161,000.00",0.00%,$0.00,"$209,300.00",
9,9788418811852,Metatrón el camino a la sabiduría cósmica,N/A,,2.00,"$144,900.00",0.00%,$0.00,"$188,370.00",
10,9788417566289,Los bisontes de Altamira,N/A,,2.00,"$161,000.00",0.00%,$0.00,"$209,300.00",
11,9788418811265,Tuareg,N/A,,2.00,"$153,000.00",0.00%,$0.00,"$198,900.00",
12,9788418811371,La condena de las élites,N/A,,2.00,"$177,100.00",0.00%,$0.00,"$230,230.00",
13,9788418263392,La vacuna,N/A,,2.00,"$136,900.00",0.00%,$0.00,"$177,970.00",
14,9788418811753,Viracocha,N/A,,2.00,"$161,000.00",0.00%,$0.00,"$209,300.00",
15,9788418263859,Memorias Cienfuegos,N/A,,2.00,"$161,000.00",0.00%,$0.00,"$209,300.00",
16,9788418263941,Serie Cienfuegos tomo 1,N/A,,2.00,"$201,200.00",0.00%,$0.00,"$261,560.00",
17,9788418811333,El sueño de Texas,N/A,,2.00,"$149,000.00",0.00%,$0.00,"$193,700.00",
18,9788416994359,Presencia y poder,N/A,,2.00,"$157,000.00",0.00%,$0.00,"$204,100.00",
19,9788417566753,Caballos en compañía,N/A,,2.00,"$177,100.00",0.00%,$0.00,"$230,230.00",
20,9788418811319,El caballo de miura,N/A,,2.00,"$209,300.00",0.00%,$0.00,"$272,090.00",
21,9788416994809,No más excusas,N/A,,2.00,"$144,900.00",0.00%,$0.00,"$188,370.00",
22,9788417566319,El domador de cerebros,N/A,,2.00,"$149,900.00",0.00%,$0.00,"$194,870.00",
23,9788417566029,Tapping la solución en tus dedos,N/A,,2.00,"$128,800.00",0.00%,$0.00,"$167,440.00",
24,9788416364534,Tocar con palabras,N/A,,1.00,"$153,000.00",0.00%,$0.00,"$99,450.00",
"""

EXTRA_CODE = "9789802717828"

def parse_csv_block(block, file_num):
    items = []
    lines = block.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = list(csv.reader([line]))[0]
        if len(row) >= 3:
            num = row[0].strip()
            code = row[1].strip()
            desc = row[2].strip()
            qty = row[5].strip() if len(row) > 5 else ""
            vr_unit = row[6].strip() if len(row) > 6 else ""
            vr_tot = row[9].strip() if len(row) > 9 else ""
            items.append({
                "archivo_origen": f"Archivo {file_num}",
                "numero_item": num,
                "codigo_buscado": code,
                "descripcion_origen": desc,
                "cantidad_origen": qty,
                "vr_unit_origen": vr_unit,
                "total_origen": vr_tot
            })
    return items

def query_shopify(graphql_query, variables=None):
    payload = {"query": graphql_query}
    if variables:
        payload["variables"] = variables
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Shopify-Access-Token": API_TOKEN,
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

SEARCH_PRODUCT_QUERY = """
query searchProduct($query: String!) {
  products(first: 5, query: $query) {
    edges {
      node {
        id
        title
        handle
        status
        vendor
        productType
        tags
        featuredImage {
          url
        }
        images(first: 10) {
          edges {
            node {
              id
              url
            }
          }
        }
        variants(first: 10) {
          edges {
            node {
              id
              title
              sku
              barcode
              price
              taxable
              image {
                url
              }
            }
          }
        }
        metafields(first: 30) {
          edges {
            node {
              id
              namespace
              key
              value
              type
            }
          }
        }
      }
    }
  }
}
"""

def clean_text(t):
    return re.sub(r"[^\w\s]", "", t.lower()).strip()

def search_product_in_shopify(code, description=None):
    try:
        res = query_shopify(SEARCH_PRODUCT_QUERY, {"query": f"{code}"})
        edges = res.get("data", {}).get("products", {}).get("edges", [])
        if edges:
            for e in edges:
                node = e["node"]
                for v in node["variants"]["edges"]:
                    vn = v["node"]
                    if (vn.get("barcode") and vn.get("barcode").strip() == code) or (vn.get("sku") and vn.get("sku").strip() == code):
                        return node, "Coincidencia exacta (Código de Barras / SKU)"
                for m in node["metafields"]["edges"]:
                    mn = m["node"]
                    if mn.get("value") and mn.get("value").strip() == code:
                        return node, f"Coincidencia exacta (Metafield {mn.get('namespace')}.{mn.get('key')})"
            
            for e in edges:
                node = e["node"]
                for v in node["variants"]["edges"]:
                    vn = v["node"]
                    if vn.get("barcode") == code or vn.get("sku") == code:
                        return node, "Coincidencia exacta (Código de Barras / SKU)"

        # 2. Try explicit barcode
        res = query_shopify(SEARCH_PRODUCT_QUERY, {"query": f"barcode:{code}"})
        edges = res.get("data", {}).get("products", {}).get("edges", [])
        if edges:
            return edges[0]["node"], "Coincidencia exacta (Barcode)"

        # 3. Try explicit SKU
        res = query_shopify(SEARCH_PRODUCT_QUERY, {"query": f"sku:{code}"})
        edges = res.get("data", {}).get("products", {}).get("edges", [])
        if edges:
            return edges[0]["node"], "Coincidencia exacta (SKU)"

        # 4. If description provided, check ONLY if exact title matches
        if description:
            clean_desc = clean_text(description)
            base_desc = re.sub(r"\bnovela\s+gr[aá]fica\b", "", clean_desc, flags=re.I).strip()
            
            res = query_shopify(SEARCH_PRODUCT_QUERY, {"query": f"title:\"{description}\""})
            edges = res.get("data", {}).get("products", {}).get("edges", [])
            for e in edges:
                node = e["node"]
                node_clean_title = clean_text(node["title"])
                node_base_title = re.sub(r"\bnovela\s+gr[aá]fica\b", "", node_clean_title, flags=re.I).strip()
                if clean_desc == node_clean_title or base_desc == node_base_title:
                    bc = node["variants"]["edges"][0]["node"].get("barcode") or "Sin barcode"
                    return node, f"Coincidencia por Título idéntico (Código en Shopify difiere: {bc})"

    except Exception as ex:
        print(f"Error buscando {code}: {ex}")

    return None, "No encontrado en Shopify"

def main():
    items = []
    items.extend(parse_csv_block(RAW_DATA_1, 1))
    items.extend(parse_csv_block(RAW_DATA_2, 2))
    items.extend(parse_csv_block(RAW_DATA_3, 3))

    items.append({
        "archivo_origen": "Código adicional solicitado",
        "numero_item": "Extra",
        "codigo_buscado": EXTRA_CODE,
        "descripcion_origen": "Alicia en el país de las maravillas (código extra solicitado)",
        "cantidad_origen": "",
        "vr_unit_origen": "",
        "total_origen": ""
    })

    print(f"Total códigos a procesar: {len(items)}")

    results = []
    exact_count = 0
    title_diff_count = 0
    not_found_count = 0

    all_raw_meta_keys = set()

    for idx, item in enumerate(items, 1):
        code = item["codigo_buscado"]
        desc = item["descripcion_origen"]

        prod_node, match_type = search_product_in_shopify(code, desc)

        row_data = {
            "archivo_origen": item["archivo_origen"],
            "item_num": item["numero_item"],
            "codigo_buscado": code,
            "descripcion_archivo": desc,
            "cantidad_archivo": item["cantidad_origen"],
            "precio_unitario_archivo": item["vr_unit_origen"],
            "total_archivo": item["total_origen"],
            "encontrado_shopify": "SÍ" if prod_node else "NO",
            "tipo_coincidencia": match_type,
            "shopify_id": "",
            "shopify_titulo": "",
            "shopify_handle": "",
            "shopify_estado": "",
            "shopify_url": "",
            "shopify_imagen_principal": "",
            "shopify_todas_imagenes": "",
            "shopify_cantidad_imagenes": 0,
            "shopify_sku": "",
            "shopify_barcode": "",
            "shopify_precio": "",
            "shopify_tiene_iva": "",
            "meta_autor": "",
            "meta_editorial": "",
            "meta_categoria": "",
            "meta_paginas": "",
            "meta_presentacion": "",
            "meta_estado": "",
            "meta_serpi": "",
            "raw_metafields": {}
        }

        if prod_node:
            if "exacta" in match_type.lower():
                exact_count += 1
            else:
                title_diff_count += 1

            row_data["shopify_id"] = prod_node.get("id", "")
            row_data["shopify_titulo"] = prod_node.get("title", "")
            row_data["shopify_handle"] = prod_node.get("handle", "")
            row_data["shopify_estado"] = prod_node.get("status", "")
            handle = prod_node.get("handle", "")
            row_data["shopify_url"] = f"{STORE_FRONTEND_URL}/products/{handle}" if handle else ""

            # Extract Images
            img_edges = prod_node.get("images", {}).get("edges", [])
            image_urls = [img["node"]["url"] for img in img_edges if img.get("node", {}).get("url")]
            
            # Featured image
            featured_img = prod_node.get("featuredImage", {})
            featured_url = featured_img.get("url") if featured_img else ""
            if not featured_url and image_urls:
                featured_url = image_urls[0]

            row_data["shopify_imagen_principal"] = featured_url or ""
            row_data["shopify_todas_imagenes"] = " | ".join(image_urls) if image_urls else ""
            row_data["shopify_cantidad_imagenes"] = len(image_urls)

            variants = prod_node.get("variants", {}).get("edges", [])
            if variants:
                matched_v = None
                for v in variants:
                    vn = v["node"]
                    if (vn.get("barcode") and vn.get("barcode").strip() == code) or (vn.get("sku") and vn.get("sku").strip() == code):
                        matched_v = vn
                        break
                if not matched_v:
                    matched_v = variants[0]["node"]

                row_data["shopify_sku"] = matched_v.get("sku") or ""
                row_data["shopify_barcode"] = matched_v.get("barcode") or ""
                row_data["shopify_precio"] = matched_v.get("price") or ""
                taxable = matched_v.get("taxable")
                row_data["shopify_tiene_iva"] = "SÍ" if taxable is True else ("NO" if taxable is False else "NO")

            meta_edges = prod_node.get("metafields", {}).get("edges", [])
            for m in meta_edges:
                mn = m["node"]
                ns = mn.get("namespace", "").lower()
                k = mn.get("key", "").lower()
                val = mn.get("value", "")
                full_key = f"{mn.get('namespace')}.{mn.get('key')}"
                row_data["raw_metafields"][full_key] = val
                all_raw_meta_keys.add(full_key)

                # Unified key mappings
                if k == "autor":
                    row_data["meta_autor"] = val
                elif k == "editorial":
                    row_data["meta_editorial"] = val
                elif k == "categoria":
                    row_data["meta_categoria"] = val
                elif k == "paginas":
                    row_data["meta_paginas"] = val
                elif k == "presentacion":
                    row_data["meta_presentacion"] = val
                elif k == "estado":
                    row_data["meta_estado"] = val
                elif k == "serpi":
                    row_data["meta_serpi"] = val
        else:
            not_found_count += 1

        results.append(row_data)

    print("\n" + "="*50)
    print(f"RESUMEN FINAL DE BÚSQUEDA:")
    print(f"  • Total códigos analizados: {len(items)}")
    print(f"  • Coincidencias exactas por código: {exact_count}")
    print(f"  • Coincidencias por título (código diferente en Shopify): {title_diff_count}")
    print(f"  • No encontrados en Shopify: {not_found_count}")
    print("="*50)

    # Columns for final CSV database including images
    headers = [
        "Archivo Origen",
        "Ítem #",
        "Código Buscado",
        "Descripción en Archivo / Factura",
        "Encontrado en Shopify",
        "Tipo de Coincidencia",
        "Título / Nombre en Shopify",
        "SKU en Shopify",
        "Código de Barras en Shopify",
        "Precio Shopify",
        "¿Tiene IVA?",
        "Enlace Página Web (URL)",
        "Enlace Imagen Principal",
        "Todas las Imágenes (URLs)",
        "Cantidad de Imágenes",
        "Metafield: Autor",
        "Metafield: Editorial",
        "Metafield: Categoría",
        "Metafield: Páginas",
        "Metafield: Presentación",
        "Metafield: Estado",
        "Metafield: Serpi",
        "Cantidad Facturada",
        "Precio Unitario Facturado",
        "Total Facturado",
        "Estado en Shopify",
        "Shopify Product ID",
        "Handle Shopify"
    ]

    output_csv = "base_datos_productos_shopify.csv"
    with open(output_csv, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in results:
            writer.writerow([
                r["archivo_origen"],
                r["item_num"],
                r["codigo_buscado"],
                r["descripcion_archivo"],
                r["encontrado_shopify"],
                r["tipo_coincidencia"],
                r["shopify_titulo"],
                r["shopify_sku"],
                r["shopify_barcode"],
                r["shopify_precio"],
                r["shopify_tiene_iva"],
                r["shopify_url"],
                r["shopify_imagen_principal"],
                r["shopify_todas_imagenes"],
                r["shopify_cantidad_imagenes"],
                r["meta_autor"],
                r["meta_editorial"],
                r["meta_categoria"],
                r["meta_paginas"],
                r["meta_presentacion"],
                r["meta_estado"],
                r["meta_serpi"],
                r["cantidad_archivo"],
                r["precio_unitario_archivo"],
                r["total_archivo"],
                r["shopify_estado"],
                r["shopify_id"],
                r["shopify_handle"]
            ])

    print(f"✅ Archivo CSV consolidado guardado en: {output_csv}")

    output_json = "base_datos_productos_shopify.json"
    with open(output_json, mode="w", encoding="utf-8") as f:
        json.dump({
            "total_items": len(items),
            "coincidencias_exactas": exact_count,
            "coincidencias_titulo_codigo_difiere": title_diff_count,
            "no_encontrados": not_found_count,
            "productos": results
        }, f, indent=2, ensure_ascii=False)
    print(f"✅ Archivo JSON consolidado guardado en: {output_json}")

if __name__ == "__main__":
    main()
