from ocr_app.runtime import InstanceLock


def test_second_instance_cannot_open_the_same_job_store(tmp_path):
    first = InstanceLock(tmp_path / 'instance.lock')
    second = InstanceLock(tmp_path / 'instance.lock')
    assert first.acquire(8765)
    try:
        assert not second.acquire(8766)
        assert second.port() == 8765
    finally:
        first.release()
    assert second.acquire(8766)
    second.release()
