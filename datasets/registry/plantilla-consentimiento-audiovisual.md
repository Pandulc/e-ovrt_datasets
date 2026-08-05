# Plantilla de consentimiento audiovisual — rodaje del banco de clips

> ✅ **NO es un pendiente (2026-08-05).** El equipo resolvió el punto por declaración: **las
> personas que aparecen en los 34 clips del rodaje son los propios integrantes del
> proyecto**, actuando según guion, sin terceros en cuadro — son a la vez los sujetos y los
> responsables del material. Lo administrativo lo maneja el equipo por su cuenta y la
> identificación del responsable va **en el informe**. Esta plantilla queda **disponible
> por si la facultad pide el formulario firmado**, no como tarea abierta.

- **Para qué es:** dejar listo, por si se pide, el instrumento que enumera **spec 43 §7
  "Marco legal"** — consentimiento libre, expreso e informado **por escrito** de cada
  persona grabada (Ley 25.326 y Disposición 10/2015), archivado y **referenciado** en
  `license_registry.md`.
- **Estado:** **borrador de trabajo, 2026-08-05.** Redactado por Claude a partir de los
  requisitos que el propio spec 43 §7 enumera. **No es asesoramiento legal**: conviene que
  lo lea alguien con formación jurídica (o la oficina correspondiente de la facultad)
  antes de hacerlo firmar. Los `[CORCHETES]` son los datos a completar.
- **Regla de manejo, no negociable:** los formularios **firmados NO van al repositorio**
  (llevan datos personales). Van al archivo físico/digital que se indique, y en el repo
  queda solo la **referencia** (identificador + ubicación), como pide spec 43 §7
  ("sin datos personales en el repo").

---

## Formulario

**CONSENTIMIENTO INFORMADO PARA LA CAPTACIÓN Y USO DE IMAGEN CON FINES ACADÉMICOS**

Lugar y fecha: **[LOCALIDAD]**, **[FECHA]**

Yo, **[NOMBRE Y APELLIDO]**, DNI **[NÚMERO]**, con domicilio en **[DOMICILIO]**, declaro
que presto mi consentimiento **libre, expreso e informado** para la captación,
almacenamiento y tratamiento de mi imagen y voz, en los términos que se detallan a
continuación.

**1. Responsable del tratamiento.** El responsable es **[NOMBRE DEL RESPONSABLE]**,
en el marco de **[INSTITUCIÓN / CARRERA / CÁTEDRA]**, con contacto en
**[CORREO ELECTRÓNICO]**.

**2. Qué se grabó y cuándo.** Grabación audiovisual realizada el **[FECHA DEL RODAJE]**
en **[LOCACIÓN]**, en la que participé de manera **actuada y voluntaria**, representando
situaciones de uso y no uso de elementos de protección personal (casco y chaleco) según un
guion previamente acordado. **Las situaciones registradas son actuadas**: no documentan
conducta laboral real de mi parte ni incumplimiento alguno de mi persona.

**3. Finalidad.** El material se usa **exclusivamente** para:
(a) construir un conjunto de evaluación ("banco de clips") con anotaciones temporales, y
medir con él el desempeño de un sistema experimental de detección de riesgos de seguridad
en obra; (b) ilustrar resultados en el informe final de la carrera, en su defensa oral y
en presentaciones académicas derivadas.
**No se usa** con fines comerciales, publicitarios ni de vigilancia, y **no** se emplea
para evaluar a personas reales ni para tomar decisiones sobre personas.

**4. Quién accede al material.** El equipo del proyecto y el tribunal evaluador. El
material **no se publica ni se redistribuye**: no se sube a repositorios públicos ni a
plataformas de video. Las imágenes que aparezcan en el informe o en la defensa se limitan a
los fotogramas necesarios para ilustrar un resultado.

**5. Carácter voluntario y consecuencias.** Mi participación es **voluntaria**. Podía
negarme sin consecuencia alguna. Si me negara, simplemente no se me habría grabado.

**6. Conservación.** El material se conserva mientras se mantenga la finalidad académica
declarada, y en todo caso hasta **[PLAZO]**, luego de lo cual se elimina o se anonimiza.

**7. Mis derechos.** Puedo ejercer en cualquier momento y de forma gratuita los derechos de
**acceso, rectificación, actualización y supresión** de mis datos, escribiendo a
**[CORREO ELECTRÓNICO]**. La revocación de este consentimiento **no** afecta la licitud del
tratamiento previo, pero implica que mi imagen deja de utilizarse en material futuro.

> *Cláusulas informativas exigidas por la normativa (verificar redacción vigente con quien
> revise el formulario):* el titular de los datos tiene la facultad de ejercer el derecho de
> acceso a ellos en forma gratuita a intervalos no inferiores a seis meses, salvo que
> acredite un interés legítimo al efecto (art. 14, inc. 3, Ley 25.326). La autoridad de
> aplicación tiene la atribución de atender las denuncias y reclamos que se interpongan
> con relación al incumplimiento de las normas sobre protección de datos personales.

**8. Declaración final.** Declaro que leí y comprendí este documento, que se me dio
oportunidad de preguntar, y que recibo una copia.

|  |  |
|---|---|
| Firma | ................................................ |
| Aclaración | ................................................ |
| DNI | ................................................ |

---

## Cómo se registra (para no meter datos personales en el repo)

1. Se hace firmar **un formulario por persona grabada**, antes o el día del rodaje.
2. Los originales firmados se archivan en **[UBICACIÓN DEL ARCHIVO, fuera del repo]**.
3. En `license_registry.md`, en la fila del rodaje, se anota únicamente:
   `consentimientos: N de N firmados y archivados en <ubicación>; ref. <identificador>` —
   **sin nombres, sin DNI, sin domicilios**.
4. Opcional y recomendable: registrar el sha256 del PDF escaneado del conjunto en el
   manifest, para que la referencia sea verificable sin exponer el contenido
   (spec 43 §9 pide "sha256 en manifest").
