import pytest

from app.chunking import split_text


def test_empty_text_returns_no_chunks() -> None:
    assert split_text("") == []


def test_short_text_is_one_chunk_with_exact_offsets() -> None:
    chunks = split_text("small document", chunk_size=30, overlap=5)
    assert len(chunks) == 1
    assert chunks[0].text == "small document"
    assert (chunks[0].start, chunks[0].end) == (0, 15)


def test_long_text_chunks_overlap_and_keep_source_offsets() -> None:
    text = " ".join(f"word{i}" for i in range(100))
    chunks = split_text(text, chunk_size=80, overlap=15)

    assert len(chunks) > 1
    for chunk in chunks:
        assert text[chunk.start:chunk.end] == chunk.text
        assert len(chunk.text) <= 80
    for previous, current in zip(chunks, chunks[1:]):
        assert current.start < previous.end


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (10, -1), (10, 10), (10, 11)],
)
def test_invalid_chunk_parameters_are_rejected(chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        split_text("some content", chunk_size=chunk_size, overlap=overlap)
