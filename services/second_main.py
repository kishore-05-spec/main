print("This is the servies")
SELECT
    r."RuleId" AS rule_id,
    r."RuleName",
    similarity(
        lower(gp."GuideLineParagraphData"),
        lower(regexp_replace(:val, '[^a-zA-Z0-9 ]', '', 'g'))
    ) AS weightage
FROM "GuidelineParagraphRules" gpr
JOIN "GuidelineParagraph" gp
    ON gpr."Paragraphid" = gp."Id"
JOIN "Rules" r
    ON gpr."RuleId" = r."Id"
WHERE
    length(regexp_replace(:val, '[^a-zA-Z0-9 ]', '', 'g')) >= 3
    AND similarity(
        lower(gp."GuideLineParagraphData"),
        lower(regexp_replace(:val, '[^a-zA-Z0-9 ]', '', 'g'))
    ) >= 0.5
ORDER BY weightage DESC;
