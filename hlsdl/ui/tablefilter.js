// Utilitários compartilhados de filtro de tabelas.
//
// A busca é dinâmica e cobre todas as colunas visíveis. Prefixos opcionais
// restringem um termo a um campo, por exemplo:
//   status:done           -> somente a coluna de status
//   erro:timeout 1080p    -> erro contém "timeout" E algum campo contém "1080p"
//
// A normalização remove acentos e diferenças de caixa, para que "compilação"
// encontre "compilacao" e vice-versa.

.pragma library

function normalize(value) {
    var text = value === null || value === undefined ? "" : String(value)
    if (text.normalize)
        text = text.normalize("NFD")
    return text.replace(/[\u0300-\u036f]/g, "").toLowerCase()
}

function tokenize(query, aliases) {
    var raw = normalize(query).trim()
    if (raw.length === 0)
        return []
    var parts = raw.split(/\s+/)
    var result = []
    for (var i = 0; i < parts.length; i++) {
        var part = parts[i]
        if (part.length === 0)
            continue
        var match = part.match(/^([a-z_]+):(.*)$/)
        if (match && match[2].length === 0)
            continue  // "status:" sozinho não deve esconder todas as linhas
        if (match && aliases && aliases[match[1]])
            result.push({ field: aliases[match[1]], term: match[2] })
        else
            result.push({ field: "", term: part })
    }
    return result
}

function allValues(fields) {
    var values = []
    for (var key in fields) {
        if (!fields.hasOwnProperty(key))
            continue
        var list = fields[key]
        for (var i = 0; i < list.length; i++)
            values.push(list[i])
    }
    return values
}

function matches(fields, tokens) {
    if (!tokens || tokens.length === 0)
        return true
    for (var i = 0; i < tokens.length; i++) {
        var token = tokens[i]
        var candidates = token.field && fields[token.field]
                         ? fields[token.field] : allValues(fields)
        var found = false
        for (var j = 0; j < candidates.length; j++) {
            if (normalize(candidates[j]).indexOf(token.term) !== -1) {
                found = true
                break
            }
        }
        if (!found)
            return false
    }
    return true
}

function matchText(query, aliases, fields) {
    return matches(fields, tokenize(query, aliases))
}
