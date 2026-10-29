# UK territory source and resource assessment

The maintained UK component comes from `https://gitlab.4corn.co.uk/RiscOS/Sources/Internat/Territory/UK.git` at `55aa82c8862f02d9db5bb4b2a9350dc8baf97192`.

The original source files and Makefile explicitly carry Acorn copyright and Apache-2.0 notices. That revision has no standalone LICENSE file, and `Resources/UK/Messages` has no individual file-level notice. The maintained copy preserves those facts; it does not invent an upstream licence file.

[uk-resource-provenance/provenance.json](uk-resource-provenance/provenance.json) identifies a later public TerritoryModule snapshot at `24e19b0ecea527441e5c72a8c945e6a1c6be99d9`. Its preserved LICENSE, Messages and Territory files corroborate the earlier resource's provenance: original token values recur apart from the obsolete TR13 placeholder and `HongKong` becoming `Hong Kong`.

That comparison is supporting evidence, not a new licence grant. Runtime bytes remain from the original UK pin. The Apache text is supplied separately in [Apache-2.0](Apache-2.0), and modified assembly files carry ArcLibre change notices. The original full assessment remains in the historical `experiments/arm2-territory/LICENSING.md` in the repository.
