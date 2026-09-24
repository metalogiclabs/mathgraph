# Semantic Object Envelope v1

Status: candidate wire contract, qualified by the MathGraph Crystal extension-stability gate.

## Purpose

The envelope is the permanent transport waist for semantic objects whose concrete
meaning may be unknown to the current runtime. Its job is not to interpret
semantics. Its job is to preserve them without loss until an implementation of
a declared semantic interface is available.

An unknown semantic type is therefore a valid object, not malformed data.

## Fields

A semantic object contains:

- `type_id`: opaque semantic type identifier.
- `contract_version`: local version of that semantic contract.
- `payload`: opaque canonical bytes defined by the type contract.
- `interfaces`: the sorted, duplicate-free set of semantic interface IDs
  implemented by the object.

The microkernel does not contain a closed enum of effect or object kinds.

## Canonical binary encoding

All integers are unsigned big-endian.

```text
6 bytes   magic = 4d 47 53 4f 00 01   ("MGSO" + envelope version 1)
u32       UTF-8 type_id byte length
bytes     UTF-8 type_id
u32       contract_version
u32       interface count
repeat interface count:
  u32     UTF-8 interface-id byte length
  bytes   UTF-8 interface-id
u64       payload byte length
bytes     opaque payload
```

Interface IDs must appear in strict canonical sorted order with no duplicates.
A decoder rejects non-canonical encodings rather than silently rewriting them.

The object identity is:

```text
semantic:SHA256(canonical-envelope-bytes)
```

Storage formats such as JSON, .mg, protobuf, database rows or in-memory structs
are projections only. They must reconstruct the same canonical envelope bytes
to preserve object identity.

## Conservative-extension rule

A runtime that does not understand the concrete semantic type must still be
able to:

1. decode the stable envelope,
2. retain the payload byte-for-byte,
3. compute and preserve content identity,
4. store and retransmit the object,
5. reference the object from provenance/evidence,
6. dispatch any semantic interfaces it does understand,
7. return a typed UNKNOWN when a requested interface is unsupported.

It must never:

- coerce an unknown object to a weaker known type,
- drop an unknown interface,
- normalize or reinterpret opaque payload bytes,
- infer authority merely because the object can be transported,
- silently substitute approximate semantics.

## Interpretation

Concrete interpretation is interface-driven, not type-enum-driven.

A runtime may learn a new interpreter in the future. Registering that interpreter
adds operations over an existing object but does not change the object's
canonical bytes or identity.

Unsupported interpretation returns an epistemic residual of the form:

```text
UNKNOWN(
  object_id = ...,
  requested_interface = ...,
  reason = "missing_interface"
)
```

## Authority boundary

The envelope describes and transports semantic objects. It creates no warrant.
Whether an object, evidence reference, refinement or consequence is live remains
an independent authority/provenance question.

## Scope

This contract establishes forward preservation for new semantic types carried
inside envelope v1. It does not claim that an unknown future envelope format can
be parsed by an implementation that only knows v1. The intended longevity
strategy is to keep this envelope waist stable and evolve semantic contracts
locally through type IDs, contract versions and interfaces.
