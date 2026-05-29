/* names.js — Fantasy name suggestions for the OtG character creator */

const NAMES_BY_SPECIES = {
  "elf": [
    "Aelindra","Adran","Berevan","Caladwen","Carric","Drannor","Erevan","Enialis",
    "Faelithil","Galadreth","Heian","Illariel","Jhaeros","Kaeldra","Liadon",
    "Mialee","Naivara","Quelenna","Riardon","Sariel","Thamior","Undolin",
    "Valanthe","Xanaphia","Yllaphine","Zylvara",
  ],
  "high elf": [
    "Aelindel","Aerindel","Caelwyn","Daeriel","Elenwe","Faelivrin","Galanodel",
    "Heianor","Ilsevel","Jaendrel","Kaendriel","Larathiel","Miandel","Naerindel",
    "Orindel","Paelianthel","Quelindel","Raelianthel","Silaqui","Taerel",
    "Ulaenith","Valanthe","Wynindel","Xanathos","Zylindra","Aelindra",
  ],
  "wood elf": [
    "Adrie","Arael","Branwyn","Caelynn","Dara","Elanil","Fenn","Galinndan",
    "Himo","Ivellios","Jandar","Keyleth","Laucian","Myriil","Nailo","Peren",
    "Quarion","Rindrel","Shava","Toross","Urnaess","Varis","Whisper",
    "Xanaphia","Yraelith","Zylvara",
  ],
  "dark elf": [
    "Drizzt","Zaknafein","Jarlaxle","Quenthel","Vierna","Triel","Yvonnel",
    "Viconia","Solaufein","Phaere","Ryltar","Nathrae","Faeryl","Elkantar",
    "Diriversa","Chalithra","Baelstra","Szordrin","Dinin","Masoj","Malice","Ilythiiri",
  ],
  "dwarf": [
    "Adrik","Baern","Darrak","Eberk","Fargrim","Gardain","Harbek","Kildrak",
    "Morgran","Orsik","Oskar","Rangrim","Rurik","Taklinn","Thoradin","Tordek",
    "Traubon","Travok","Ulfgar","Veit","Gurdis","Helja","Kathra","Kristryd","Mardred",
  ],
  "hill dwarf": [
    "Aldren","Barrek","Brorn","Dagmar","Dorthon","Edda","Filden","Grunna",
    "Harmon","Ilda","Jorn","Kettrin","Liftrasa","Mundorak","Norren","Ottrik",
    "Raenna","Sannl","Torbera","Torinn","Ulfen","Vondra","Welda","Yorra",
  ],
  "mountain dwarf": [
    "Aldur","Bormek","Drangrak","Durgin","Garnok","Gormek","Grundal","Haldur",
    "Kolgrim","Mordak","Narek","Ordrak","Rangal","Roric","Sondrak","Storvald",
    "Thordek","Torvald","Uldar","Verda","Vistra","Wrenna","Ygrek","Zornak",
  ],
  "halfling": [
    "Alton","Ander","Cade","Corrin","Eldon","Errich","Finnan","Garret","Lindal",
    "Lyle","Merric","Milo","Osborn","Perrin","Reed","Roscoe","Wellby","Callie",
    "Cora","Euphemia","Jillian","Kithri","Lavinia","Lidda","Merla",
  ],
  "lightfoot halfling": [
    "Ambrose","Basil","Beau","Birch","Cheery","Clem","Dalton","Dilly","Ember",
    "Emmett","Fern","Flora","Lark","Maple","Ned","Penny","Poppy","Rory",
    "Rue","Sage","Thistle","Willa","Woody","Yarrow",
  ],
  "stout halfling": [
    "Aldric","Bram","Brin","Cedar","Clay","Dell","Durwen","Flint","Greta",
    "Hazel","Hollis","Kirk","Linden","Molly","Mose","Nori","Orben","Paddy",
    "Petra","Rona","Stone","Tam","Wade","Wynn",
  ],
  "gnome": [
    "Alston","Alvyn","Boddynock","Brocc","Burgell","Dimble","Ellywick","Erky",
    "Fonkin","Frug","Gerbo","Gimble","Glim","Jebeddo","Namfoodle","Orryn",
    "Roondar","Seebo","Sindri","Warryn","Wrenn","Zook","Bimpnottin","Breena","Caramip",
  ],
  "half-elf": [
    "Adra","Aelindra","Bree","Carric","Dara","Erevan","Faral","Gared","Halia",
    "Ilara","Jhaeros","Kira","Liadon","Mira","Naivara","Orin","Paelias",
    "Quelenna","Reva","Sariel","Thalion","Ulen","Velorin","Wren","Zephyr",
  ],
  "half-orc": [
    "Dench","Feng","Gell","Henk","Holg","Imsh","Keth","Krusk","Mhurren",
    "Ront","Shump","Thokk","Baggi","Emen","Engong","Kansif","Myev","Neega",
    "Ovak","Ownka","Shautha","Yevelda",
  ],
  "tiefling": [
    "Akta","Anakis","Bryseis","Criella","Damaia","Kallista","Lerissa","Makaria",
    "Nemeia","Orianna","Phelaia","Rieta","Zara","Akmenos","Amnon","Barakas",
    "Damakos","Ekemon","Iados","Kairon","Leucis","Melech","Mordai","Morthos","Therai",
  ],
  "dragonborn": [
    "Arjhan","Balasar","Bharash","Donaar","Ghesh","Heskan","Kriv","Medrash",
    "Mehen","Nadarr","Pandjed","Patrin","Rhogar","Shamash","Shedinn","Tarhun",
    "Torinn","Biri","Daar","Farideh","Havilar","Jheri","Kava","Korinn","Mishann",
  ],
  "human": [
    "Aldric","Brennan","Corwyn","Daran","Edmund","Favian","Garrett","Hadrian",
    "Ivan","Jareth","Kellan","Lucan","Marcus","Nikolai","Oswin","Pierce",
    "Quentin","Roland","Soren","Tobias","Ulric","Vance","Aldara","Bryn",
    "Calla","Deva","Elara","Fiona","Gwynn","Hana",
  ],
  "default": [
    "Aelindra","Aldric","Arjhan","Bryn","Caelynn","Corwyn","Daran","Elara",
    "Erevan","Faelan","Garrett","Gwynn","Hadrian","Hana","Heskan","Ilara",
    "Janna","Kira","Kriv","Lena","Liadon","Lucan","Marcus","Mira","Nadarr",
    "Nora","Orla","Pierce","Quelenna","Roland","Sariel","Soren","Tara",
    "Thamior","Tobias","Ulric","Valanthe","Vance","Wren","Yara","Zara",
    "Alaric","Briar","Calyx","Dusk","Ember","Flynn","Gale","Haven","Iris",
  ],
};

function suggestName(species) {
  const key  = (species || "").toLowerCase().trim();
  const list = NAMES_BY_SPECIES[key] || NAMES_BY_SPECIES["default"];
  return list[Math.floor(Math.random() * list.length)];
}
